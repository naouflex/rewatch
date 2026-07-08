"""Tests for assistant thread persistence."""

from rewatch.assistant import storage
from rewatch.models import AssistantMessage, db
from tests import BaseTestCase


class TestAssistantStorage(BaseTestCase):
    def test_save_user_message_commits_before_reply(self):
        user = self.factory.create_user()
        thread = storage.create_thread(user, self.factory.org)

        storage.save_user_message(thread.id, "What is the weather?")

        db.session.expire_all()
        messages = (
            AssistantMessage.query.filter(AssistantMessage.thread_id == thread.id)
            .order_by(AssistantMessage.id)
            .all()
        )

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, "What is the weather?")
