from flask import make_response, request
from flask_restful import abort
from sqlalchemy.exc import IntegrityError

from redash import models
from redash.destinations import (
    destinations,
    get_configuration_schema_for_destination_type,
)
from redash.handlers.base import BaseResource, get_object_or_404, require_fields
from redash.permissions import require_admin_or_owner, require_permission
from redash.utils.configuration import ConfigurationContainer, ValidationError


def serialize_destinations(current_user, destinations, all=False):
    destinations = list(destinations)
    favorite_ids = set(models.Favorite.are_favorites(current_user.id, destinations))
    result = []
    for destination in destinations:
        d = destination.to_dict(all=all)
        d["is_favorite"] = destination.id in favorite_ids
        result.append(d)
    return result


class DestinationTypeListResource(BaseResource):
    @require_permission("list_destinations")
    def get(self):
        return [q.to_dict() for q in destinations.values()]


class DestinationResource(BaseResource):
    @require_permission("view_destination")
    def get(self, destination_id):
        destination = get_object_or_404(
            models.NotificationDestination.get_by_id_and_org, destination_id, self.current_org
        )
        require_admin_or_owner(destination.user_id)
        d = destination.to_dict(all=True)
        d["is_favorite"] = models.Favorite.is_favorite(self.current_user.id, destination)
        self.record_event(
            {
                "action": "view",
                "object_id": destination_id,
                "object_type": "destination",
            }
        )
        return d

    @require_permission("edit_destination")
    def post(self, destination_id):
        destination = get_object_or_404(
            models.NotificationDestination.get_by_id_and_org, destination_id, self.current_org
        )
        require_admin_or_owner(destination.user_id)
        req = request.get_json(True)

        if "name" in req:
            destination.name = req["name"]

        if "tags" in req:
            destination.tags = req["tags"]

        if "type" in req and "options" in req:
            schema = get_configuration_schema_for_destination_type(req["type"])
            if schema is None:
                abort(400)
            try:
                destination.type = req["type"]
                destination.options.set_schema(schema)
                destination.options.update(req["options"])
            except ValidationError:
                abort(400)

        try:
            models.db.session.add(destination)
            models.db.session.commit()
        except IntegrityError as e:
            if "name" in str(e):
                abort(
                    400,
                    message="Alert Destination with the name {} already exists.".format(req.get("name")),
                )
            abort(500)

        return destination.to_dict(all=True)

    @require_permission("edit_destination")
    def delete(self, destination_id):
        destination = get_object_or_404(
            models.NotificationDestination.get_by_id_and_org, destination_id, self.current_org
        )
        require_admin_or_owner(destination.user_id)
        models.db.session.delete(destination)
        models.db.session.commit()

        self.record_event(
            {
                "action": "delete",
                "object_id": destination_id,
                "object_type": "destination",
            }
        )

        return make_response("", 204)


class DestinationListResource(BaseResource):
    @require_permission("list_destinations")
    def get(self):
        if self.current_user.has_permission("admin"):
            destinations = models.NotificationDestination.all(self.current_org)
        else:
            destinations = models.NotificationDestination.by_user(self.current_user)

        self.record_event(
            {
                "action": "list",
                "object_id": "admin/destinations",
                "object_type": "destination",
            }
        )

        return serialize_destinations(self.current_user, destinations)

    @require_permission("create_destination")
    def post(self):
        req = request.get_json(True)
        require_fields(req, ("options", "name", "type"))

        schema = get_configuration_schema_for_destination_type(req["type"])
        if schema is None:
            abort(400)

        config = ConfigurationContainer(req["options"], schema)
        if not config.is_valid():
            abort(400)

        destination = models.NotificationDestination(
            org=self.current_org,
            name=req["name"],
            type=req["type"],
            options=config,
            user=self.current_user,
            tags=req.get("tags"),
        )

        try:
            models.db.session.add(destination)
            models.db.session.commit()
        except IntegrityError as e:
            if "name" in str(e):
                abort(
                    400,
                    message="Alert Destination with the name {} already exists.".format(req["name"]),
                )
            abort(500)

        return destination.to_dict(all=True)


class MyDestinationsResource(BaseResource):
    @require_permission("list_destinations")
    def get(self):
        destinations = models.NotificationDestination.by_user(self.current_user)
        self.record_event(
            {
                "action": "list",
                "object_type": "destination",
                "filter": "my",
            }
        )
        return serialize_destinations(self.current_user, destinations)


class DestinationFavoriteListResource(BaseResource):
    @require_permission("list_destinations")
    def get(self):
        destinations = models.NotificationDestination.favorites(self.current_user)
        self.record_event({"action": "load_favorites", "object_type": "destination"})
        return serialize_destinations(self.current_user, destinations)


class DestinationArchiveResource(BaseResource):
    def post(self, destination_id):
        destination = get_object_or_404(
            models.NotificationDestination.get_by_id_and_org, destination_id, self.current_org
        )
        require_admin_or_owner(destination.user_id)

        destination.archive()
        models.db.session.commit()
        self.record_event(
            {"action": "archive", "object_id": destination.id, "object_type": "destination"}
        )
        return destination.to_dict()


class DestinationArchivedListResource(BaseResource):
    @require_permission("list_destinations")
    def get(self):
        if self.current_user.has_permission("admin"):
            destinations = models.NotificationDestination.all(self.current_org, include_archived=True)
        else:
            destinations = models.NotificationDestination.by_user(self.current_user, include_archived=True)
        destinations = destinations.filter(models.NotificationDestination.is_archived.is_(True))
        self.record_event({"action": "list", "object_type": "destination", "filter": "archived"})
        return serialize_destinations(self.current_user, destinations)


class DestinationTagsResource(BaseResource):
    @require_permission("list_destinations")
    def get(self):
        tags = models.NotificationDestination.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class DestinationFavoriteResource(BaseResource):
    def post(self, destination_id):
        destination = get_object_or_404(
            models.NotificationDestination.get_by_id_and_org, destination_id, self.current_org
        )
        require_admin_or_owner(destination.user_id)

        fav = models.Favorite(org_id=self.current_org.id, object=destination, user=self.current_user)
        models.db.session.add(fav)

        try:
            models.db.session.commit()
        except IntegrityError as e:
            if "unique_favorite" in str(e):
                models.db.session.rollback()
            else:
                raise e

        self.record_event(
            {"action": "favorite", "object_id": destination.id, "object_type": "destination"}
        )

    def delete(self, destination_id):
        destination = get_object_or_404(
            models.NotificationDestination.get_by_id_and_org, destination_id, self.current_org
        )
        require_admin_or_owner(destination.user_id)

        models.Favorite.query.filter(
            models.Favorite.object_id == destination_id,
            models.Favorite.object_type == "NotificationDestination",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()

        self.record_event(
            {"action": "unfavorite", "object_id": destination.id, "object_type": "destination"}
        )
