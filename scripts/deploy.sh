#!/usr/bin/env bash
# scripts/deploy.sh — provision and operate rewatch on a Google Cloud VM.
#
# Mirrors every step in DEPLOY.md and adds an optional HTTPS phase that puts
# Caddy in front of the rewatch `server` container with an automatically
# renewing Let's Encrypt certificate for $REDASH_HOST (read from .env).
#
# All phases are idempotent. Run a single phase at a time, or `all` for the
# happy-path first-time deploy.
#
# Usage:
#   scripts/deploy.sh provision        # create VM + firewall rules
#   scripts/deploy.sh install          # install Docker on the VM
#   scripts/deploy.sh upload           # scp the project (incl. .env)
#   scripts/deploy.sh authorize-db     # whitelist VM IP on Cloud SQL
#   scripts/deploy.sh init             # build + create_db + up -d
#   scripts/deploy.sh build            # docker compose build (ml-worker last)
#   scripts/deploy.sh start            # docker compose up -d
#   scripts/deploy.sh push             # re-upload + restart (no rebuild, fast)
#   scripts/deploy.sh update [--build-frontend]  # re-upload, rebuild, restart
#                                      # (--build-frontend / -b also rebuilds client/dist on the VM)
#   scripts/deploy.sh build-frontend   # build client/dist on the VM (node container)
#   scripts/deploy.sh status           # docker compose ps
#   scripts/deploy.sh logs [service]   # tail logs (default: server)
#   scripts/deploy.sh https            # provision Caddy + Let's Encrypt
#   scripts/deploy.sh https-logs       # tail Caddy logs (cert progress)
#   scripts/deploy.sh ip               # print the VM's external IP
#   scripts/deploy.sh ssh              # open an SSH shell on the VM
#   scripts/deploy.sh ssh-config       # add 'rewatch-prod' to ~/.ssh/config (Cursor Remote-SSH)
#   scripts/deploy.sh all              # provision + install + upload + init
#
# Environment overrides:
#   INSTANCE          GCE instance name (default: rewatch-prod)
#   ZONE              GCE zone          (default: europe-west1-b)
#   MACHINE_TYPE      VM machine type   (default: e2-standard-2)
#   IMAGE_FAMILY      OS image family   (default: debian-12)
#   IMAGE_PROJECT     OS image project  (default: debian-cloud)
#   BOOT_DISK_SIZE                      (default: 50GB)
#   APP_PORT          Rewatch host port  (default: 5001)
#   REMOTE_DIR        Remote directory  (default: rewatch)
#   CLOUD_SQL_INSTANCE Cloud SQL name to whitelist VM IP on (default: watch-db)
#   LETSENCRYPT_EMAIL Override the cert registration email
#                     (defaults to REDASH_MAIL_DEFAULT_SENDER from .env)
set -euo pipefail

# ---------- defaults ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INSTANCE="${INSTANCE:-rewatch-prod}"
ZONE="${ZONE:-europe-west1-b}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
IMAGE_FAMILY="${IMAGE_FAMILY:-debian-12}"
IMAGE_PROJECT="${IMAGE_PROJECT:-debian-cloud}"
BOOT_DISK_SIZE="${BOOT_DISK_SIZE:-50GB}"
TAGS="${TAGS:-http-server,https-server}"
APP_PORT="${APP_PORT:-5001}"
REMOTE_DIR="${REMOTE_DIR:-rewatch}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-watch-db}"

# ---------- ui helpers --------------------------------------------------------
if [[ -t 1 ]]; then
  C_BLUE=$'\033[1;34m'; C_YELLOW=$'\033[1;33m'; C_RED=$'\033[1;31m'
  C_GREEN=$'\033[1;32m'; C_RESET=$'\033[0m'
else
  C_BLUE=""; C_YELLOW=""; C_RED=""; C_GREEN=""; C_RESET=""
fi
log()  { printf "%s[deploy]%s %s\n" "$C_BLUE"   "$C_RESET" "$*"; }
ok()   { printf "%s[ ok  ]%s %s\n" "$C_GREEN"  "$C_RESET" "$*"; }
warn() { printf "%s[warn ]%s %s\n" "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()  { printf "%s[fail ]%s %s\n" "$C_RED"    "$C_RESET" "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

# ---------- gcloud helpers ----------------------------------------------------
ssh_vm() {
  # run a command on the VM; quoting is the caller's responsibility
  gcloud compute ssh "$INSTANCE" --zone="$ZONE" --quiet --command="$1"
}

# Run `docker compose <args>` on the VM, automatically including the HTTPS
# overlay if it has been deployed (compose.https.yaml present on the VM).
# This keeps Caddy in scope so it's never flagged as an orphan during update,
# push, start, status or logs once HTTPS has been set up. Pass the full
# subcommand string as a single argument, e.g.:
#   vm_compose 'up -d'
#   vm_compose 'build server worker scheduler'
#   vm_compose 'logs --tail=200 -f server'
vm_compose() {
  ssh_vm "cd ~/$REMOTE_DIR && \
    files='-f compose.yaml'; \
    [ -f compose.https.yaml ] && files=\"\$files -f compose.https.yaml\"; \
    docker compose \$files $1"
}

# Build the frontend on the VM inside a throwaway container that matches the
# Dockerfile's frontend-builder stage (node:24 + pnpm@10.30.3). It writes
# ./client/dist on the VM via a bind mount, which the bind-mounted `server`
# container then serves directly. node_modules is excluded from the upload
# tarball, so a full `pnpm install` runs first. webpack is memory-hungry; on a
# small VM this can OOM — prefer building locally and uploading when it does.
vm_build_frontend() {
  log "Building frontend on $INSTANCE in a node:24 container (pnpm install + build)..."
  # Install pnpm into a project-local prefix so the container can run as the VM
  # user (-u) without needing root for a global npm install.
  ssh_vm "cd ~/$REMOTE_DIR && docker run --rm -u \"\$(id -u):\$(id -g)\" -v \"\$PWD\":/app -w /app node:24-bookworm \
    bash -lc 'mkdir -p .npm-global && npm config set prefix \"\$PWD/.npm-global\" && npm install -g pnpm@10.30.3 && export PATH=\"\$PWD/.npm-global/bin:\$PATH\" && pnpm install --frozen-lockfile && pnpm run build'"
  ok "Frontend built into ~/$REMOTE_DIR/client/dist."
}

vm_external_ip() {
  gcloud compute instances describe "$INSTANCE" --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null
}

firewall_exists() {
  gcloud compute firewall-rules describe "$1" >/dev/null 2>&1
}

instance_exists() {
  gcloud compute instances describe "$INSTANCE" --zone="$ZONE" >/dev/null 2>&1
}

# Poll SSH on the VM until it accepts a no-op command. Freshly created GCE
# instances return STATUS=RUNNING before sshd is listening, which causes a
# "Connection refused" on the first command. Default budget: ~3 minutes.
wait_for_ssh() {
  local max_attempts="${1:-18}"
  local interval="${2:-10}"
  local attempt=1
  log "Waiting for SSH to become ready on $INSTANCE (up to $((max_attempts * interval))s)..."
  while (( attempt <= max_attempts )); do
    if gcloud compute ssh "$INSTANCE" --zone="$ZONE" --quiet \
         --ssh-flag="-o ConnectTimeout=5" \
         --ssh-flag="-o StrictHostKeyChecking=accept-new" \
         --command='true' >/dev/null 2>&1; then
      ok "SSH ready (attempt $attempt)."
      return 0
    fi
    log "  attempt $attempt/$max_attempts: not ready yet, retrying in ${interval}s..."
    sleep "$interval"
    attempt=$((attempt + 1))
  done
  die "SSH did not become available on $INSTANCE within $((max_attempts * interval))s"
}

# Read a KEY=value line from .env and strip surrounding quotes.
read_env_var() {
  local key="$1"
  [[ -f "$ENV_FILE" ]] || return 1
  awk -F= -v k="$key" '
    $0 !~ /^[[:space:]]*#/ && $1 == k {
      sub(/^[^=]+=/, "")
      gsub(/^"|"$/, "")
      gsub(/^\047|\047$/, "")
      print
      exit
    }
  ' "$ENV_FILE"
}

# ---------- phase: provision --------------------------------------------------
cmd_provision() {
  require_cmd gcloud

  local just_created=0
  log "Ensuring VM $INSTANCE exists in zone $ZONE..."
  if instance_exists; then
    ok "VM $INSTANCE already exists, skipping create."
  else
    gcloud compute instances create "$INSTANCE" \
      --machine-type="$MACHINE_TYPE" \
      --image-family="$IMAGE_FAMILY" \
      --image-project="$IMAGE_PROJECT" \
      --boot-disk-size="$BOOT_DISK_SIZE" \
      --tags="$TAGS" \
      --zone="$ZONE"
    just_created=1
    ok "VM created."
  fi

  log "Ensuring firewall rule allow-rewatch (tcp:$APP_PORT)..."
  if firewall_exists allow-rewatch; then
    ok "allow-rewatch already exists."
  else
    gcloud compute firewall-rules create allow-rewatch \
      --allow="tcp:$APP_PORT" \
      --target-tags=http-server
  fi

  log "Ensuring firewall rule allow-https-rewatch (tcp:80,443) for Let's Encrypt..."
  if firewall_exists allow-https-rewatch; then
    ok "allow-https-rewatch already exists."
  else
    gcloud compute firewall-rules create allow-https-rewatch \
      --allow=tcp:80,tcp:443 \
      --target-tags=http-server
  fi

  local ip
  ip="$(vm_external_ip || true)"
  [[ -n "$ip" ]] && ok "External IP: $ip"

  if (( just_created )); then
    wait_for_ssh
  fi
}

# ---------- phase: install ----------------------------------------------------
cmd_install() {
  require_cmd gcloud
  instance_exists || die "VM $INSTANCE not found; run 'provision' first."

  wait_for_ssh
  log "Installing Docker on $INSTANCE (idempotent)..."
  ssh_vm '
    set -e
    if ! command -v docker >/dev/null 2>&1; then
      curl -fsSL https://get.docker.com | sh
    else
      echo "docker already installed: $(docker --version)"
    fi
    if ! id -nG "$USER" | tr " " "\n" | grep -qx docker; then
      sudo usermod -aG docker "$USER"
      echo "added $USER to docker group; new SSH sessions will inherit it"
    else
      echo "$USER is already in the docker group"
    fi
  '
  ok "Docker ready."
}

# ---------- phase: upload -----------------------------------------------------
# Excludes for the upload tarball. node_modules (~1.3 GB) is generated by the
# docker frontend-builder stage. .git, virtualenvs, caches and IDE state are
# never read at runtime. client/dist/ IS shipped because compose.yaml sets
# `skip_frontend_build: "true"` and bind-mounts ./ over /app inside the
# container, so the built assets must already exist on the host filesystem.
UPLOAD_EXCLUDES=(
  --exclude=./node_modules
  --exclude=./viz-lib/node_modules
  --exclude=./.git
  --exclude=./.venv
  --exclude=./venv
  --exclude=./.cache
  --exclude=./.npm-global
  --exclude=./.tmp
  --exclude=./client/.tmp
  --exclude=./client/cypress/screenshots
  --exclude=./client/cypress/videos
  --exclude=./.coverage
  --exclude=./.coverage.*
  --exclude=./coverage
  --exclude=./coverage.xml
  --exclude=./.nyc_output
  --exclude=./.idea
  --exclude=./.vscode
  --exclude=./.cursor
  --exclude=./.DS_Store
  --exclude=./dump.rdb
  --exclude=__pycache__
  --exclude=*.pyc
)

cmd_upload() {
  require_cmd gcloud
  require_cmd tar
  instance_exists || die "VM $INSTANCE not found; run 'provision' first."
  [[ -f "$ENV_FILE" ]] || warn "$ENV_FILE not found; production secrets will be missing on the VM."

  if [[ ! -f "$PROJECT_ROOT/client/dist/index.html" ]]; then
    warn "client/dist/index.html missing — the prod compose runs with"
    warn "skip_frontend_build=true and bind-mounts ./ over /app, so the"
    warn "frontend must be built locally first: pnpm install && pnpm run build"
  fi

  log "Streaming project to $INSTANCE:~/$REMOTE_DIR (gzipped tar over ssh, excludes node_modules/.git/etc)..."
  # vm_build_frontend and docker bind mounts leave files under client/dist owned
  # by root; plain tar extraction then fails with "File exists" / "Operation not
  # permitted". Drop the tree and fix ownership before unpacking.
  ssh_vm "mkdir -p ~/$REMOTE_DIR && \
    sudo rm -rf ~/$REMOTE_DIR/client/dist && \
    sudo chown -R \$USER:\$USER ~/$REMOTE_DIR 2>/dev/null || true"
  tar -C "$PROJECT_ROOT" "${UPLOAD_EXCLUDES[@]}" -czf - . \
    | gcloud compute ssh "$INSTANCE" --zone="$ZONE" --quiet \
        --command="tar -xzf - -C ~/$REMOTE_DIR --overwrite"

  log "Verifying .env landed on the VM..."
  ssh_vm "test -f ~/$REMOTE_DIR/.env && echo 'env ok' || (echo 'MISSING .env on VM' >&2; exit 1)"
  ok "Project uploaded."
}

# ---------- phase: authorize-db ----------------------------------------------
# Cloud SQL only accepts connections from IPs explicitly listed in its
# Authorized Networks. This phase appends the VM's external IP to the existing
# list (idempotent — re-running with an already-whitelisted IP is a no-op).
cmd_authorize_db() {
  require_cmd gcloud
  instance_exists || die "VM $INSTANCE not found; run 'provision' first."

  if ! gcloud sql instances describe "$CLOUD_SQL_INSTANCE" >/dev/null 2>&1; then
    die "Cloud SQL instance '$CLOUD_SQL_INSTANCE' not found. Set CLOUD_SQL_INSTANCE=<name> or skip this phase."
  fi

  local vm_ip cidr existing combined
  vm_ip="$(vm_external_ip || true)"
  [[ -n "$vm_ip" ]] || die "Could not determine VM external IP."
  cidr="$vm_ip/32"

  existing="$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" \
    --format='value(settings.ipConfiguration.authorizedNetworks[].value)' \
    2>/dev/null | tr ';\t\n' ',,,' | sed 's/,\+/,/g; s/^,//; s/,$//')"

  if [[ ",$existing," == *",$cidr,"* ]]; then
    ok "$cidr is already authorized on Cloud SQL '$CLOUD_SQL_INSTANCE'."
    return 0
  fi

  combined="${existing:+$existing,}$cidr"
  log "Authorizing $cidr on Cloud SQL '$CLOUD_SQL_INSTANCE'..."
  log "  existing: ${existing:-(none)}"
  log "  new list: $combined"
  gcloud sql instances patch "$CLOUD_SQL_INSTANCE" \
    --authorized-networks="$combined" --quiet
  ok "Cloud SQL authorized networks updated."
}

# ---------- phase: init -------------------------------------------------------
# Build ordering matters: ml-worker's Dockerfile.ml is `FROM rewatch-worker:latest`,
# so the worker image must exist locally before ml-worker is built. `docker
# compose build` runs services in parallel by default and ignores depends_on,
# which makes ml-worker race ahead and try to pull rewatch-worker:latest from
# Docker Hub (where it doesn't exist). We do it in two passes instead.
cmd_build() {
  vm_compose 'build server worker scheduler'
  vm_compose 'build ml-worker'
}

cmd_init() {
  log "Building base images (server, worker, scheduler)..."
  vm_compose 'build server worker scheduler'
  log "Building ml-worker (depends on rewatch-worker:latest)..."
  vm_compose 'build ml-worker'
  log "Running first-time database setup..."
  vm_compose 'run --rm server create_db'
  log "Starting services..."
  vm_compose 'up -d'
  ok "Stack is up. Use 'status' or 'logs' to inspect."
}

# ---------- phase: start / update / status / logs ----------------------------
cmd_start()  { vm_compose 'up -d'; }
cmd_status() { vm_compose 'ps'; }
cmd_logs()   {
  local svc="${1:-server}"
  vm_compose "logs --tail=200 -f $svc"
}

cmd_update() {
  local build_frontend=0
  while (( $# )); do
    case "$1" in
      --build-frontend|-b) build_frontend=1 ;;
      *) warn "update: ignoring unknown argument '$1'" ;;
    esac
    shift
  done

  log "Re-uploading project and rebuilding..."
  cmd_upload
  if (( build_frontend )); then
    vm_build_frontend
  fi
  log "Rebuilding base images then ml-worker..."
  vm_compose 'build server worker scheduler'
  vm_compose 'build ml-worker'
  vm_compose 'up -d'
  ok "Update applied."
}

# Build the frontend on the VM without re-uploading or rebuilding images.
# Useful to refresh client/dist in place after an upload/push.
cmd_build_frontend() {
  require_cmd gcloud
  instance_exists || die "VM $INSTANCE not found; run 'provision' first."
  vm_build_frontend
}

# Fast iteration: re-upload code and restart the Python services without
# rebuilding any docker image. Safe whenever the changes are limited to
# files that are bind-mounted at runtime (compose.yaml has `volumes: - .:/app`)
# — i.e. plain Python sources, templates, settings, and pre-built client/dist.
# Use `update` instead when you change pyproject.toml, poetry.lock, the
# Dockerfile, or any other content that's baked into the image at build time.
cmd_push() {
  log "Pushing code (no rebuild)..."
  cmd_upload
  log "Restarting Python services..."
  vm_compose 'up -d --remove-orphans server worker scheduler ml-worker'
  ok "Push complete. Tail logs with: $0 logs server"
}

cmd_ip()  { vm_external_ip; }
cmd_ssh() { gcloud compute ssh "$INSTANCE" --zone="$ZONE"; }

# Populate ~/.ssh/config so plain `ssh rewatch-prod`, scp, rsync and editors
# like Cursor/VS Code Remote-SSH can reach the VM without going through gcloud.
# This is the same key gcloud uses (~/.ssh/google_compute_engine), but exposed
# under a short, stable alias matching $INSTANCE.
cmd_ssh_config() {
  require_cmd gcloud
  instance_exists || die "VM $INSTANCE not found; run 'provision' first."

  log "Running 'gcloud compute config-ssh' to register GCE hosts in ~/.ssh/config..."
  gcloud compute config-ssh --quiet >/dev/null

  local long_host host_key_alias ip
  long_host="$INSTANCE.$ZONE.$(gcloud config get-value project 2>/dev/null)"
  host_key_alias="$(awk -v h="$long_host" '
    $1=="Host" { in_block = ($2==h) }
    in_block && tolower($1) ~ /^hostkeyalias=?/ {
      sub(/.*HostKeyAlias[ =]+/, "")
      print; exit
    }' ~/.ssh/config | tr -d ' =')"
  ip="$(vm_external_ip)"
  [[ -n "$host_key_alias" ]] || die "Could not extract HostKeyAlias for $long_host."

  if grep -q "^Host $INSTANCE\$" ~/.ssh/config 2>/dev/null; then
    ok "Short alias 'Host $INSTANCE' already present in ~/.ssh/config."
  else
    log "Prepending short alias 'Host $INSTANCE' to ~/.ssh/config..."
    local tmp; tmp="$(mktemp)"
    {
      printf '# Short alias for the GCE %s VM (managed by scripts/deploy.sh).\n' "$INSTANCE"
      printf 'Host %s\n' "$INSTANCE"
      printf '    HostName %s\n' "$ip"
      printf '    User %s\n' "${USER:-$(whoami)}"
      printf '    IdentityFile ~/.ssh/google_compute_engine\n'
      printf '    UserKnownHostsFile ~/.ssh/google_compute_known_hosts\n'
      printf '    IdentitiesOnly yes\n'
      printf '    CheckHostIP no\n'
      printf '    HostKeyAlias %s\n' "$host_key_alias"
      printf '    ServerAliveInterval 30\n'
      printf '    ServerAliveCountMax 4\n\n'
      cat ~/.ssh/config 2>/dev/null
    } >"$tmp"
    mv "$tmp" ~/.ssh/config
    chmod 600 ~/.ssh/config
    ok "Alias added."
  fi

  log "Verifying connectivity..."
  if ssh -o BatchMode=yes -o ConnectTimeout=8 "$INSTANCE" 'true'; then
    ok "ssh $INSTANCE works. You can now use it from Cursor (Remote-SSH), rsync, scp, etc."
  else
    die "ssh $INSTANCE failed. Inspect ~/.ssh/config manually."
  fi
}

# ---------- phase: https (Caddy + Let's Encrypt) ------------------------------
# Caddy ships with automatic HTTPS — it provisions a Let's Encrypt cert on
# first start and renews it before expiry. It runs as an extra docker compose
# service that joins the same network as `server` and reverse-proxies to
# server:5000 (the in-container port; 5001 is just the host mapping).
cmd_https() {
  require_cmd gcloud
  instance_exists || die "VM $INSTANCE not found; run 'provision' first."

  local host domain email ip
  host="$(read_env_var REDASH_HOST || true)"
  [[ -n "$host" ]] || die "REDASH_HOST not found in $ENV_FILE"
  domain="${host#https://}"
  domain="${domain#http://}"
  domain="${domain%/}"

  email="${LETSENCRYPT_EMAIL:-$(read_env_var REDASH_MAIL_DEFAULT_SENDER || true)}"
  [[ -n "$email" ]] || die "Set LETSENCRYPT_EMAIL or REDASH_MAIL_DEFAULT_SENDER in .env"

  ip="$(vm_external_ip || true)"
  [[ -n "$ip" ]] || die "Could not determine VM external IP."

  log "Domain : $domain"
  log "Email  : $email"
  log "VM IP  : $ip"
  warn "Make sure '$domain' has an A record pointing to $ip BEFORE running this phase,"
  warn "otherwise Let's Encrypt's HTTP-01 challenge will fail."

  if ! firewall_exists allow-https-rewatch; then
    log "Creating firewall rule allow-https-rewatch..."
    gcloud compute firewall-rules create allow-https-rewatch \
      --allow=tcp:80,tcp:443 --target-tags=http-server
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir:-}"' RETURN

  cat >"$tmpdir/Caddyfile" <<EOF
{
    email $email
}

$domain {
    encode zstd gzip
    reverse_proxy server:5000
}
EOF

  cat >"$tmpdir/compose.https.yaml" <<'EOF'
# Overlay that adds an HTTPS-terminating Caddy in front of `server`.
# Use with: docker compose -f compose.yaml -f compose.https.yaml up -d
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - server
volumes:
  caddy_data:
  caddy_config:
EOF

  log "Uploading Caddyfile and compose.https.yaml..."
  ssh_vm "mkdir -p ~/$REMOTE_DIR/caddy"
  gcloud compute scp --zone="$ZONE" --quiet \
    "$tmpdir/Caddyfile" "$INSTANCE:$REMOTE_DIR/caddy/Caddyfile"
  gcloud compute scp --zone="$ZONE" --quiet \
    "$tmpdir/compose.https.yaml" "$INSTANCE:$REMOTE_DIR/compose.https.yaml"

  log "Bringing up Caddy + rewatch stack with HTTPS overlay..."
  vm_compose 'up -d'

  ok "Caddy launched. Watch certificate provisioning with:"
  echo "  $0 https-logs"
  echo
  echo "Once you see 'certificate obtained successfully' for $domain,"
  echo "browse to https://$domain and verify the cert chain is valid."
}

cmd_https_logs() {
  vm_compose 'logs --tail=200 -f caddy'
}

# ---------- phase: all --------------------------------------------------------
cmd_all() {
  cmd_provision
  cmd_install
  cmd_upload
  cmd_authorize_db
  cmd_init
  cmd_status
  echo
  ok "First-time deploy complete. Optional next step:"
  echo "  $0 https     # provision Let's Encrypt cert via Caddy"
}

# ---------- usage / dispatch --------------------------------------------------
usage() {
  sed -n '2,37p' "$0" | sed 's/^# \{0,1\}//'
}

main() {
  local cmd="${1:-}"
  [[ -n "$cmd" ]] || { usage; exit 1; }
  shift || true
  case "$cmd" in
    provision)  cmd_provision ;;
    install)    cmd_install ;;
    upload)     cmd_upload ;;
    authorize-db) cmd_authorize_db ;;
    init)       cmd_init ;;
    build)      cmd_build ;;
    build-frontend) cmd_build_frontend ;;
    start)      cmd_start ;;
    push)       cmd_push ;;
    update)     cmd_update "$@" ;;
    status)     cmd_status ;;
    logs)       cmd_logs "$@" ;;
    https)      cmd_https ;;
    https-logs) cmd_https_logs ;;
    ip)         cmd_ip ;;
    ssh)        cmd_ssh ;;
    ssh-config) cmd_ssh_config ;;
    all)        cmd_all ;;
    -h|--help|help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
