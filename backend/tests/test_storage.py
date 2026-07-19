import sqlite3
import unittest
from pathlib import Path

from backend.storage import RuntimeStore

TEST_DATABASE_PATH = Path("backend/tests/runtime-test.db").resolve()


class RuntimeStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = RuntimeStore(TEST_DATABASE_PATH)
        self.store.initialize()
        with sqlite3.connect(TEST_DATABASE_PATH) as connection:
            connection.execute("DELETE FROM chat_messages")
            connection.execute("DELETE FROM activities")
            connection.execute("DELETE FROM tasks")
            connection.execute("DELETE FROM agents")

    def test_agents_are_persistent_and_upsertable(self):
        self.store.seed_agents(
            [
                {
                    "id": "programmer",
                    "name": "Programmer",
                    "role": "programmer",
                    "description": "Writes code",
                    "model": "model-a",
                }
            ]
        )
        self.store.upsert_agent(
            {
                "id": "programmer",
                "name": "Lead Programmer",
                "role": "programmer",
                "description": "Writes production code",
                "model": "model-b",
                "status": "busy",
            }
        )

        reopened = RuntimeStore(TEST_DATABASE_PATH)
        agents = reopened.list_agents()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["name"], "Lead Programmer")
        self.assertEqual(agents[0]["model"], "model-b")
        self.assertEqual(agents[0]["status"], "busy")

    def test_activity_retention_and_order(self):
        self.store.add_activity("Agent", "started", "first")
        self.store.add_activity("Agent", "completed", "second")
        activities = self.store.list_activities()
        self.assertEqual([item["detail"] for item in activities], ["second", "first"])

    def test_task_crud(self):
        task = self.store.create_task("Ship beta", "Finish the slice", "todo", "manager")
        self.assertTrue(self.store.update_task(task["id"], {"status": "in_progress"}))
        self.assertEqual(self.store.list_tasks()[0]["status"], "in_progress")
        self.assertTrue(self.store.delete_task(task["id"]))
        self.assertEqual(self.store.list_tasks(), [])

    def test_chat_history_replaces_canonical_session(self):
        self.store.replace_session_messages(
            "agent:programmer:main",
            "programmer",
            [
                {"role": "user", "content": "Build it"},
                {"role": "assistant", "content": "Done"},
            ],
        )
        messages = self.store.list_session_messages("agent:programmer:main")
        self.assertEqual([item["content"] for item in messages], ["Build it", "Done"])


if __name__ == "__main__":
    unittest.main()
