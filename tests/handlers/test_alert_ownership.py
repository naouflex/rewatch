"""Tests covering the "ownable" handlers added to the Alert resource:

- Archiving an alert.
- Tagging alerts and listing tags.
- Marking alerts as favorite (and listing them).
- Listing the alerts owned by the current user (``/api/alerts/my``).
"""
from rewatch.models import Alert, Favorite, db
from tests import BaseTestCase


class TestAlertTagsAndUpdate(BaseTestCase):
    def test_can_save_and_retrieve_tags_via_resource(self):
        alert = self.factory.create_alert()
        tags = ["prod", "billing"]

        rv = self.make_request("post", "/api/alerts/{}".format(alert.id), data={"tags": tags})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(sorted(rv.json["tags"]), sorted(tags))

        rv = self.make_request("get", "/api/alerts/{}".format(alert.id))
        self.assertEqual(sorted(rv.json["tags"]), sorted(tags))

    def test_alert_tags_endpoint_aggregates_usage(self):
        self.factory.create_alert(tags=["prod", "billing"])
        self.factory.create_alert(tags=["prod"])
        db.session.commit()

        rv = self.make_request("get", "/api/alerts/tags")
        self.assertEqual(rv.status_code, 200)
        names = sorted(t["name"] for t in rv.json["tags"])
        self.assertIn("prod", names)
        self.assertIn("billing", names)


class TestAlertArchive(BaseTestCase):
    def test_archive_marks_alert_archived_and_excludes_it_from_listing(self):
        alert = self.factory.create_alert()

        rv = self.make_request("post", "/api/alerts/{}/archive".format(alert.id))
        self.assertEqual(rv.status_code, 200)
        self.assertTrue(rv.json["is_archived"])

        listing = self.make_request("get", "/api/alerts").json
        self.assertNotIn(alert.id, [a["id"] for a in listing])

    def test_only_owner_or_admin_can_archive(self):
        alert = self.factory.create_alert()
        other_user = self.factory.create_user()

        rv = self.make_request(
            "post", "/api/alerts/{}/archive".format(alert.id), user=other_user
        )
        self.assertEqual(rv.status_code, 403)

        admin = self.factory.create_admin()
        rv = self.make_request(
            "post", "/api/alerts/{}/archive".format(alert.id), user=admin
        )
        self.assertEqual(rv.status_code, 200)


class TestAlertFavorite(BaseTestCase):
    def test_favorite_and_unfavorite_round_trip(self):
        alert = self.factory.create_alert()

        rv = self.make_request("post", "/api/alerts/{}/favorite".format(alert.id))
        self.assertEqual(rv.status_code, 200)

        favorite = (
            db.session.query(Favorite)
            .filter(
                Favorite.object_type == "Alert",
                Favorite.object_id == alert.id,
                Favorite.user_id == self.factory.user.id,
            )
            .first()
        )
        self.assertIsNotNone(favorite)

        rv = self.make_request("get", "/api/alerts/favorites")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(alert.id, [a["id"] for a in rv.json])
        self.assertTrue(rv.json[0]["is_favorite"])

        rv = self.make_request("delete", "/api/alerts/{}/favorite".format(alert.id))
        self.assertEqual(rv.status_code, 200)

        favorite = (
            db.session.query(Favorite)
            .filter(
                Favorite.object_type == "Alert",
                Favorite.object_id == alert.id,
            )
            .first()
        )
        self.assertIsNone(favorite)

    def test_favoriting_twice_does_not_blow_up(self):
        alert = self.factory.create_alert()
        self.make_request("post", "/api/alerts/{}/favorite".format(alert.id))
        rv = self.make_request("post", "/api/alerts/{}/favorite".format(alert.id))
        self.assertEqual(rv.status_code, 200)


class TestMyAlerts(BaseTestCase):
    def test_my_endpoint_returns_only_alerts_owned_by_current_user(self):
        alert = self.factory.create_alert()
        other = self.factory.create_user()
        self.factory.create_alert(user=other)
        db.session.commit()

        rv = self.make_request("get", "/api/alerts/my")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual([a["id"] for a in rv.json], [alert.id])


class TestAlertListExcludesArchived(BaseTestCase):
    def test_archived_alerts_are_excluded_from_default_listing(self):
        alert = self.factory.create_alert()
        archived = self.factory.create_alert()
        archived.is_archived = True
        db.session.commit()

        rv = self.make_request("get", "/api/alerts")
        ids = [a["id"] for a in rv.json]
        self.assertIn(alert.id, ids)
        self.assertNotIn(archived.id, ids)
