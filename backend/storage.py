"""SQLite persistence for the PerfectBlue local runtime."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable


class RuntimeStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_lock = threading.Lock()
        self._initialized = False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._initialize_lock:
            if self._initialized:
                return
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS agents (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        role TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        model TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'online',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent TEXT NOT NULL,
                        action TEXT NOT NULL,
                        detail TEXT NOT NULL DEFAULT '',
                        created_at REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'todo',
                        assignee_id TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at REAL NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_activities_created_at
                    ON activities(created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session
                    ON chat_messages(session_id, id);
                    """
                )
            self._initialized = True

    def seed_agents(self, agents: Iterable[dict[str, Any]]) -> None:
        self.initialize()
        now = time.time()
        with self._connect() as connection:
            for agent in agents:
                connection.execute(
                    """
                    INSERT INTO agents (
                        id, name, role, description, model, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    """,
                    (
                        agent["id"],
                        agent["name"],
                        agent["role"],
                        agent.get("description", ""),
                        agent["model"],
                        agent.get("status", "online"),
                        now,
                        now,
                    ),
                )

    def list_agents(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, role, description, model, status, created_at, updated_at
                FROM agents
                ORDER BY created_at, id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_agent(self, agent: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        now = time.time()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM agents WHERE id = ?", (agent["id"],)
            ).fetchone()
            created_at = float(existing["created_at"]) if existing else now
            connection.execute(
                """
                INSERT INTO agents (
                    id, name, role, description, model, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    description = excluded.description,
                    model = excluded.model,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    agent["id"],
                    agent["name"],
                    agent["role"],
                    agent.get("description", ""),
                    agent["model"],
                    agent.get("status", "online"),
                    created_at,
                    now,
                ),
            )
        return {**agent, "created_at": created_at, "updated_at": now}

    def delete_agent(self, agent_id: str) -> bool:
        self.initialize()
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        return cursor.rowcount > 0

    def add_activity(self, agent: str, action: str, detail: str) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO activities (agent, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (agent, action, detail, time.time()),
            )
            connection.execute(
                """
                DELETE FROM activities
                WHERE id NOT IN (
                    SELECT id FROM activities ORDER BY created_at DESC, id DESC LIMIT 200
                )
                """
            )

    def list_activities(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        safe_limit = min(max(limit, 1), 200)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, agent, action, detail, created_at
                FROM activities
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_tasks(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, description, status, assignee_id, created_at, updated_at
                FROM tasks ORDER BY id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_task(
        self,
        title: str,
        description: str,
        status: str,
        assignee_id: str | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (
                    title, description, status, assignee_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, description, status, assignee_id, now, now),
            )
            task_id = int(cursor.lastrowid)
        return {
            "id": task_id,
            "title": title,
            "description": description,
            "status": status,
            "assignee_id": assignee_id,
            "created_at": now,
            "updated_at": now,
        }

    def update_task(self, task_id: int, updates: dict[str, Any]) -> bool:
        self.initialize()
        allowed = {"title", "description", "status", "assignee_id"}
        fields = [(key, value) for key, value in updates.items() if key in allowed]
        if not fields:
            return False
        assignments = ", ".join(f"{key} = ?" for key, _ in fields)
        values = [value for _, value in fields]
        values.extend([time.time(), task_id])
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE tasks SET {assignments}, updated_at = ? WHERE id = ?",
                values,
            )
        return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        self.initialize()
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0

    def replace_session_messages(
        self,
        session_id: str,
        agent_id: str,
        messages: Iterable[dict[str, Any]],
    ) -> None:
        self.initialize()
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM chat_messages WHERE session_id = ?", (session_id,)
            )
            for index, message in enumerate(messages):
                role = str(message.get("role", "user"))
                content = str(message.get("content", ""))
                if not content:
                    continue
                connection.execute(
                    """
                    INSERT INTO chat_messages (
                        session_id, agent_id, role, content, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, agent_id, role, content, now + (index / 1000)),
                )

    def list_session_messages(self, session_id: str) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, agent_id, role, content, created_at
                FROM chat_messages WHERE session_id = ? ORDER BY id
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]
