import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.security import (
    WorkspaceSecurityError,
    ensure_workspace_read_allowed,
    resolve_workspace_path,
)

TEST_WORKSPACE = Path("backend/tests/security-workspace").resolve()


class WorkspaceSecurityTests(unittest.TestCase):
    def test_rejects_parent_traversal(self):
        with self.assertRaises(WorkspaceSecurityError):
            resolve_workspace_path(TEST_WORKSPACE, "../escape.txt")

    def test_requires_agent_writes_to_use_project_directory(self):
        with self.assertRaises(WorkspaceSecurityError):
            resolve_workspace_path(
                TEST_WORKSPACE,
                "output.txt",
                require_project_path=True,
            )

        resolved = resolve_workspace_path(
            TEST_WORKSPACE,
            "projects/demo/output.txt",
            require_project_path=True,
        )
        self.assertEqual(resolved, TEST_WORKSPACE / "projects/demo/output.txt")

    def test_legacy_root_write_override_is_explicit(self):
        with patch.dict(os.environ, {"PERFECTBLUE_ALLOW_ROOT_WRITES": "true"}):
            resolved = resolve_workspace_path(
                TEST_WORKSPACE,
                "output.txt",
                require_project_path=True,
            )
        self.assertEqual(resolved, TEST_WORKSPACE / "output.txt")

    def test_blocks_environment_secrets_and_private_state(self):
        with self.assertRaises(WorkspaceSecurityError):
            ensure_workspace_read_allowed(TEST_WORKSPACE, TEST_WORKSPACE / ".env")
        with self.assertRaises(WorkspaceSecurityError):
            ensure_workspace_read_allowed(
                TEST_WORKSPACE,
                TEST_WORKSPACE / ".perfectblue/perfectblue.db",
            )

        ensure_workspace_read_allowed(TEST_WORKSPACE, TEST_WORKSPACE / ".env.example")
        ensure_workspace_read_allowed(TEST_WORKSPACE, TEST_WORKSPACE / "src/main.py")


if __name__ == "__main__":
    unittest.main()
