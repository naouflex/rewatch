from flask import render_template, send_file
from flask_login import login_required
from werkzeug.utils import safe_join

from rewatch import settings
from rewatch.handlers import routes
from rewatch.handlers.authentication import base_href
from rewatch.handlers.base import org_scoped_rule
from rewatch.security import csp_allows_embeding


def render_index():
    if settings.MULTI_ORG:
        response = render_template("multi_org.html", base_href=base_href())
    else:
        full_path = safe_join(settings.STATIC_ASSETS_PATH, "index.html")
        response = send_file(full_path, **dict(max_age=0, conditional=True))

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
