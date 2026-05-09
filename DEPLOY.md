# Deploying to a Google Cloud VM

Quick recipe for running the production `compose.yaml` on a GCE instance.

## 1. Create the VM

```bash
gcloud compute instances create redash-prod \
  --machine-type=e2-standard-2 \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=50GB \
  --tags=http-server,https-server \
  --zone=europe-west1-b
```

Open the app port (Redash listens on `5001` per `compose.yaml`):

```bash
gcloud compute firewall-rules create allow-redash \
  --allow=tcp:5001 --target-tags=http-server
```

## 2. Install Docker on the VM

```bash
gcloud compute ssh redash-prod --zone=europe-west1-b
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && exit   # log out so the group takes effect
```

## 3. Upload the project

From your laptop:

```bash
gcloud compute scp --recurse --compress \
  --zone=europe-west1-b \
  ./ redash-prod:~/redash
```

`.env` is in `.gitignore` but `scp --recurse` copies it; double-check it landed
on the VM and that secrets inside are the production values (`REDASH_HOST`,
`REDASH_DATABASE_URL`, mail creds, `REDASH_COOKIE_SECRET`,
`REDASH_SECRET_KEY`).

## 4. First-run database setup

SSH back in and from `~/redash`:

```bash
docker compose build
docker compose run --rm server create_db   # only the very first time
docker compose up -d
```

Check status / logs:

```bash
docker compose ps
docker compose logs -f server
```

## 5. Updates

```bash
git pull                    # or re-run the scp from step 3
docker compose build
docker compose up -d
```

## 6. (Optional) HTTPS

Put an HTTPS-terminating proxy in front of port `5001`. Easiest options:

- A Google Cloud HTTPS Load Balancer pointing at the VM.
- Caddy / Nginx on the VM with a Let's Encrypt cert for `REDASH_HOST`
  (`watch.naoufel.io` in this project's `.env`).
