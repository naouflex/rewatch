from rewatch import models
from tests import BaseTestCase


class WidgetAPITest(BaseTestCase):
    def create_widget(self, dashboard, visualization, width=1):
        data = {
            "visualization_id": visualization.id,
            "dashboard_id": dashboard.id,
            "options": {},
            "width": width,
        }

        rv = self.make_request("post", "/api/widgets", data=data)

        return rv

    def test_create_widget(self):
        dashboard = self.factory.create_dashboard()
        vis = self.factory.create_visualization()

        rv = self.create_widget(dashboard, vis)
        self.assertEqual(rv.status_code, 200)

    def test_wont_create_widget_for_visualization_you_dont_have_access_to(self):
        dashboard = self.factory.create_dashboard()
        vis = self.factory.create_visualization()
        ds = self.factory.create_data_source(group=self.factory.create_group())
        vis.query_rel.data_source = ds

        models.db.session.add(vis.query_rel)

        data = {
            "visualization_id": vis.id,
            "dashboard_id": dashboard.id,
            "options": {},
            "width": 1,
        }

        rv = self.make_request("post", "/api/widgets", data=data)
        self.assertEqual(rv.status_code, 403)

    def test_create_text_widget(self):
        dashboard = self.factory.create_dashboard()

        data = {
            "visualization_id": None,
            "text": "Sample text.",
            "dashboard_id": dashboard.id,
            "options": {},
            "width": 2,
        }

        rv = self.make_request("post", "/api/widgets", data=data)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["text"], "Sample text.")

    def test_delete_widget(self):
        widget = self.factory.create_widget()

        rv = self.make_request("delete", "/api/widgets/{0}".format(widget.id))

        self.assertEqual(rv.status_code, 200)
        dashboard = models.Dashboard.get_by_slug_and_org(widget.dashboard.slug, widget.dashboard.org)
        self.assertEqual(dashboard.widgets.count(), 0)

    def test_update_widget_options_without_text(self):
        widget = self.factory.create_widget(
            options={"position": {"col": 0, "row": 0, "sizeX": 6, "sizeY": 3}}
        )
        data = {
            "options": {
                "position": {"col": 6, "row": 0, "sizeX": 6, "sizeY": 3, "minSizeX": 2, "maxSizeX": 12},
            }
        }
        rv = self.make_request("post", f"/api/widgets/{widget.id}", data=data)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["options"]["position"]["col"], 6)

    def test_create_widget_auto_places_with_numeric_position(self):
        dashboard = self.factory.create_dashboard()
        vis = self.factory.create_visualization()

        rv = self.create_widget(dashboard, vis)
        self.assertEqual(rv.status_code, 200)
        pos = rv.json["options"]["position"]
        self.assertIsInstance(pos["col"], int)
        self.assertIsInstance(pos["row"], int)
        self.assertIsInstance(pos["sizeX"], int)
        self.assertIsInstance(pos["sizeY"], int)

    def test_get_widget(self):
        widget = self.factory.create_widget()
        rv = self.make_request("get", f"/api/widgets/{widget.id}")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["id"], widget.id)
