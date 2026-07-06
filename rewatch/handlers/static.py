from flask import jsonify, render_template, request, send_file
from flask_login import login_required
from werkzeug.utils import safe_join

from rewatch import settings
from rewatch.handlers import routes
from rewatch.handlers.authentication import base_href
from rewatch.handlers.base import org_scoped_rule
from rewatch.security import csp_allows_embeding

PWA_THEME_COLOR = "#ff7230"
PWA_BACKGROUND_COLOR = "#ffffff"
PWA_APP_NAME = "Rewatch"


def render_index():
    if settings.MULTI_ORG:
        response = render_template("multi_org.html", base_href=base_href())
    else:
        full_path = safe_join(settings.STATIC_ASSETS_PATH, "index.html")
        response = send_file(full_path, **dict(max_age=0, conditional=True))

    return response


@routes.route("/manifest.webmanifest")
def web_app_manifest():
    start_url = base_href() if settings.MULTI_ORG else "/"
    manifest = {
        "id": start_url,
        "name": PWA_APP_NAME,
        "short_name": PWA_APP_NAME,
        "description": "Data platform for queries, dashboards, and alerts.",
        "start_url": start_url,
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "theme_color": PWA_THEME_COLOR,
        "background_color": PWA_BACKGROUND_COLOR,
        "categories": ["business", "productivity"],
        "icons": [
            {
                "src": "/static/images/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/images/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    response = jsonify(manifest)
    response.mimetype = "application/manifest+json"
    return response


def configure_pwa(app):
    @app.after_request
    def pwa_response_headers(response):
        if request.path.endswith("/service-worker.js"):
            response.headers["Service-Worker-Allowed"] = "/"
            response.headers["Cache-Control"] = "no-cache"
        return response


@routes.route(org_scoped_rule("/dashboard/<slug>"), methods=["GET"])
@login_required
@csp_allows_embeding
def dashboard(slug, org_slug=None):
    return render_index()


@routes.route(org_scoped_rule("/<path:path>"))
@routes.route(org_scoped_rule("/"))
@login_required
def index(**kwargs):
    return render_index()
