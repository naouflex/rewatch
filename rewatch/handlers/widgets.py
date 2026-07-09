from flask import request

from rewatch import models
from rewatch.assistant.dashboard_layout import prepare_widget_options, prepare_widget_options_for_update
from rewatch.handlers.base import BaseResource
from rewatch.permissions import (
    require_access,
    require_object_modify_permission,
    require_permission,
    view_only,
)
from rewatch.serializers import serialize_dashboard, serialize_widget


def _dashboard_widgets(dashboard, user=None):
    return [
        w
        for w in (serialize_dashboard(dashboard, with_widgets=True, user=user).get("widgets") or [])
        if isinstance(w, dict)
    ]


def _prepare_widget_options(dashboard, visualization, text, options, user=None):
    return prepare_widget_options(
        _dashboard_widgets(dashboard, user=user),
        visualization_type=visualization.type if visualization else None,
        text=text,
        options=options,
    )


class WidgetListResource(BaseResource):
    @require_permission("edit_dashboard")
    def post(self):
        """
        Add a widget to a dashboard.

        :<json number dashboard_id: The ID for the dashboard being added to
        :<json visualization_id: The ID of the visualization to put in this widget
        :<json object options: Widget options
        :<json string text: Text box contents
        :<json number width: Width for widget display

        :>json object widget: The created widget
        """
        widget_properties = request.get_json(force=True)
        dashboard = models.Dashboard.get_by_id_and_org(widget_properties.get("dashboard_id"), self.current_org)
        require_object_modify_permission(dashboard, self.current_user)

        widget_properties.pop("id", None)

        visualization_id = widget_properties.pop("visualization_id", None)
        if visualization_id:
            visualization = models.Visualization.get_by_id_and_org(visualization_id, self.current_org)
            require_access(visualization.query_rel, self.current_user, view_only)
        else:
            visualization = None

        widget_properties["visualization"] = visualization
        widget_properties["options"] = _prepare_widget_options(
            dashboard,
            visualization,
            widget_properties.get("text"),
            widget_properties.get("options"),
            user=self.current_user,
        )

        widget = models.Widget(**widget_properties)
        models.db.session.add(widget)

        models.db.session.commit()
        return serialize_widget(widget)


class WidgetResource(BaseResource):
    @require_permission("view_dashboard")
    def get(self, widget_id):
        """
        Get a single dashboard widget (layout options and linked visualization).

        :param number widget_id: The ID of the widget
        """
        widget = models.Widget.get_by_id_and_org(widget_id, self.current_org)
        if widget.visualization_id:
            require_access(widget.visualization.query_rel, self.current_user, view_only)
        return serialize_widget(widget)

    @require_permission("edit_dashboard")
    def post(self, widget_id):
        """
        Updates a widget on a dashboard (text box content and/or layout options).

        :param number widget_id: The ID of the widget to modify

        :<json string text: The new contents of a text box (optional)
        :<json object options: Widget options including position (optional)
        """
        widget = models.Widget.get_by_id_and_org(widget_id, self.current_org)
        require_object_modify_permission(widget.dashboard, self.current_user)
        widget_properties = request.get_json(force=True)
        if "text" in widget_properties:
            widget.text = widget_properties["text"]
        if "options" in widget_properties:
            widget.options = prepare_widget_options_for_update(
                serialize_widget(widget),
                _dashboard_widgets(widget.dashboard, user=self.current_user),
                visualization_type=widget.visualization.type if widget.visualization else None,
                text=widget_properties.get("text", widget.text),
                options=widget_properties["options"],
            )
        models.db.session.commit()
        return serialize_widget(widget)

    @require_permission("edit_dashboard")
    def delete(self, widget_id):
        """
        Remove a widget from a dashboard.

        :param number widget_id: ID of widget to remove
        """
        widget = models.Widget.get_by_id_and_org(widget_id, self.current_org)
        require_object_modify_permission(widget.dashboard, self.current_user)
        self.record_event({"action": "delete", "object_id": widget_id, "object_type": "widget"})
        models.db.session.delete(widget)
        models.db.session.commit()
