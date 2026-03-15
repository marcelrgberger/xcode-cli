"""Session state management for Xcode CLI harness."""

import json
from datetime import datetime, timezone
from pathlib import Path


class Session:
    """Tracks the current session state for the Xcode CLI harness.

    Maintains the current workspace reference, active scheme, command history,
    and provides serialisation for session persistence.
    """

    def __init__(self) -> None:
        """Initialize a new empty session."""
        self._workspace_name: str | None = None
        self._workspace_path: str | None = None
        self._active_scheme: str | None = None
        self._active_destination: str | None = None
        self._history: list[dict] = []
        self._created_at: str = datetime.now(timezone.utc).isoformat()

    def set_workspace(self, name: str, path: str | None = None) -> None:
        """Set the current active workspace.

        Args:
            name: The workspace name.
            path: Optional file path to the workspace.
        """
        self._workspace_name = name
        self._workspace_path = path

    def get_workspace(self) -> str | None:
        """Get the name of the current active workspace.

        Returns:
            str or None: The current workspace name, or None if not set.
        """
        return self._workspace_name

    def set_active_scheme(self, scheme: str) -> None:
        """Set the active scheme name.

        Args:
            scheme: Scheme name.
        """
        self._active_scheme = scheme

    def get_active_scheme(self) -> str | None:
        """Get the active scheme name.

        Returns:
            str or None: The active scheme name.
        """
        return self._active_scheme

    def set_active_destination(self, destination: str) -> None:
        """Set the active run destination.

        Args:
            destination: Destination name.
        """
        self._active_destination = destination

    def get_active_destination(self) -> str | None:
        """Get the active run destination.

        Returns:
            str or None: The active destination name.
        """
        return self._active_destination

    def status(self) -> dict:
        """Get the current session status.

        Returns:
            dict: Session state with keys: workspace_name, workspace_path,
                  active_scheme, active_destination, created_at, command_count.
        """
        return {
            "workspace_name": self._workspace_name,
            "workspace_path": self._workspace_path,
            "active_scheme": self._active_scheme,
            "active_destination": self._active_destination,
            "created_at": self._created_at,
            "command_count": len(self._history),
        }

    def save_session(self, path: str) -> None:
        """Save the session state to a JSON file.

        Args:
            path: File path to save the session to.
        """
        data = {
            "workspace_name": self._workspace_name,
            "workspace_path": self._workspace_path,
            "active_scheme": self._active_scheme,
            "active_destination": self._active_destination,
            "created_at": self._created_at,
            "history": self._history,
        }
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load_session(self, path: str) -> None:
        """Load a session state from a JSON file.

        Args:
            path: File path to load the session from.

        Raises:
            FileNotFoundError: If the session file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        file_path = Path(path)
        data = json.loads(file_path.read_text(encoding="utf-8"))

        self._workspace_name = data.get("workspace_name")
        self._workspace_path = data.get("workspace_path")
        self._active_scheme = data.get("active_scheme")
        self._active_destination = data.get("active_destination")
        self._created_at = data.get("created_at", self._created_at)
        self._history = data.get("history", [])

    def add_to_history(self, command: str) -> None:
        """Add a command to the session history.

        Args:
            command: The command string that was executed.
        """
        self._history.append({
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_history(self) -> list[dict]:
        """Get the command history.

        Returns:
            list[dict]: List of history entries, each with keys: command, timestamp.
        """
        return list(self._history)
