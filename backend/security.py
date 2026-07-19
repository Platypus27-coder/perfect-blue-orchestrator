"""Security helpers for the local PerfectBlue runtime."""

from __future__ import annotations

import os
from pathlib import Path


class WorkspaceSecurityError(ValueError):
    """Raised when a tool attempts to escape the configured workspace."""


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_workspace_path(
    workspace_dir: str | Path,
    relative_path: str,
    *,
    require_project_path: bool = False,
) -> Path:
    """Resolve a user supplied path and guarantee it remains in the workspace.

    Writes created by agents are project-scoped by default. Operators can keep
    legacy behavior temporarily with ``PERFECTBLUE_ALLOW_ROOT_WRITES=true``.
    """

    workspace = Path(workspace_dir).resolve()
    raw = (relative_path or "").strip()
    if not raw:
        raise WorkspaceSecurityError("Đường dẫn không được để trống.")

    candidate = (workspace / raw).resolve()
    try:
        relative = candidate.relative_to(workspace)
    except ValueError as exc:
        raise WorkspaceSecurityError(
            "Không được phép truy cập tệp ngoài thư mục dự án."
        ) from exc

    if require_project_path and not env_flag("PERFECTBLUE_ALLOW_ROOT_WRITES"):
        parts = relative.parts
        if not parts or parts[0].lower() != "projects" or len(parts) < 2:
            raise WorkspaceSecurityError(
                "Tệp do agent tạo phải nằm trong projects/<tên_dự_án>/."
            )

    return candidate


def ensure_workspace_read_allowed(workspace_dir: str | Path, candidate: str | Path) -> None:
    """Block files that commonly contain secrets or private runtime state."""

    workspace = Path(workspace_dir).resolve()
    resolved = Path(candidate).resolve()
    try:
        relative = resolved.relative_to(workspace)
    except ValueError as exc:
        raise WorkspaceSecurityError(
            "Không được phép truy cập tệp ngoài thư mục dự án."
        ) from exc

    lowered_parts = [part.lower() for part in relative.parts]
    blocked_directories = {".git", ".perfectblue", "node_modules", "__pycache__"}
    if any(part in blocked_directories for part in lowered_parts[:-1]):
        raise WorkspaceSecurityError("Không được phép đọc thư mục private hoặc dependency.")

    filename = lowered_parts[-1] if lowered_parts else ""
    is_environment_secret = filename == ".env" or (
        filename.startswith(".env.") and not filename.endswith(".example")
    )
    secret_suffixes = {".pem", ".key", ".p12", ".pfx"}
    secret_filenames = {
        "credentials.json",
        "service-account.json",
        "service_account.json",
        "id_rsa",
        "id_ed25519",
    }
    if (
        is_environment_secret
        or filename in secret_filenames
        or Path(filename).suffix in secret_suffixes
    ):
        raise WorkspaceSecurityError("Không được phép đọc tệp secret.")


def sanitize_subprocess_environment() -> dict[str, str]:
    """Return a minimal environment without API keys for optional code runs."""

    allowed_names = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "LANG",
    }
    return {key: value for key, value in os.environ.items() if key.upper() in allowed_names}
