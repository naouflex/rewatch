from flask import jsonify
from flask_login import login_required

from rewatch.handlers.api import api
from rewatch.handlers.base import routes
from rewatch.handlers.swagger import setup_swagger
from rewatch.monitor import get_status
from rewatch.permissions import require_super_admin
from rewatch.security import talisman


@routes.route("/ping", methods=["GET"])
@talisman(force_https=False)
def ping():
    return "PONG."


@routes.route("/status.json")
@login_required
@require_super_admin
def status_api():
    status = get_status()
    return jsonify(status)


def init_app(app):
    from rewatch.handlers import (
        admin,
        authentication,
        embed,
        organization,
        queries,
        setup,
        static,
    )

    app.register_blueprint(routes)
    api.init_app(app)
    setup_swagger(app)
