"""Workspace and project operations for Xcode.

Uses AppleScript to query Xcode's workspace document model for schemes,
run destinations, projects, targets, and build configurations.
Uses xcodebuild for listing schemes/targets when no workspace is open.
"""

from pathlib import Path

from xcode_cli.utils.xcode_backend import (
    _run_applescript,
    _run_xcodebuild,
    ensure_xcode_running,
)


def list_workspaces() -> list[dict]:
    """List open workspace documents in Xcode.

    Returns:
        List of dicts with keys: name, path, loaded.
    """
    ensure_xcode_running()
    count_str = _run_applescript(
        'tell application "Xcode" to count of workspace documents'
    )
    count = int(count_str) if count_str.isdigit() else 0

    workspaces = []
    for i in range(1, count + 1):
        try:
            name = _run_applescript(
                f'tell application "Xcode" to get name of workspace document {i}'
            )
            loaded = _run_applescript(
                f'tell application "Xcode" to get loaded of workspace document {i}'
            )
            try:
                path = _run_applescript(
                    f'tell application "Xcode" to get path of workspace document {i}'
                )
            except RuntimeError:
                path = ""
            workspaces.append({
                "name": name,
                "path": path,
                "loaded": loaded.lower() == "true",
                "index": i,
            })
        except RuntimeError:
            continue

    return workspaces


def get_active_scheme() -> str:
    """Get the name of the active scheme in the frontmost workspace.

    Returns:
        str: The active scheme name, or empty string if none.
    """
    ensure_xcode_running()
    try:
        return _run_applescript(
            'tell application "Xcode" to get name of active scheme of '
            'front workspace document'
        )
    except RuntimeError:
        return ""


def set_active_scheme(name: str) -> dict:
    """Set the active scheme by name.

    Args:
        name: The scheme name to activate.

    Returns:
        Dict with result information.
    """
    ensure_xcode_running()
    _run_applescript(
        f'tell application "Xcode"\n'
        f'  set ws to front workspace document\n'
        f'  repeat with s in schemes of ws\n'
        f'    if name of s is "{name}" then\n'
        f'      set active scheme of ws to s\n'
        f'      return name of s\n'
        f'    end if\n'
        f'  end repeat\n'
        f'end tell'
    )
    return {"scheme": name, "message": f"Active scheme set to: {name}"}


def get_active_run_destination() -> dict:
    """Get the active run destination of the frontmost workspace.

    Returns:
        Dict with keys: name, architecture, platform, device_name,
        device_identifier, os_version, model_name, generic.
    """
    ensure_xcode_running()
    try:
        name = _run_applescript(
            'tell application "Xcode" to get name of active run destination '
            'of front workspace document'
        )
    except RuntimeError:
        return {}

    result = {"name": name}

    for prop in ["architecture", "platform"]:
        try:
            val = _run_applescript(
                f'tell application "Xcode" to get {prop} of active run destination '
                f'of front workspace document'
            )
            result[prop] = val
        except RuntimeError:
            result[prop] = ""

    # Device properties
    for prop, key in [
        ("name", "device_name"),
        ("identifier", "device_identifier"),
        ("operating system version", "os_version"),
        ("model name", "model_name"),
        ("generic", "generic"),
    ]:
        try:
            val = _run_applescript(
                f'tell application "Xcode" to get {prop} of device of '
                f'active run destination of front workspace document'
            )
            result[key] = val
        except RuntimeError:
            result[key] = ""

    return result


def list_schemes() -> list[dict]:
    """List all schemes in the frontmost workspace.

    Returns:
        List of dicts with keys: name, id.
    """
    ensure_xcode_running()
    try:
        names_str = _run_applescript(
            'tell application "Xcode" to get name of every scheme '
            'of front workspace document'
        )
    except RuntimeError:
        return []

    if not names_str:
        return []

    names = [n.strip() for n in names_str.split(",")]

    schemes = []
    for i, name in enumerate(names, 1):
        try:
            scheme_id = _run_applescript(
                f'tell application "Xcode" to get id of scheme {i} '
                f'of front workspace document'
            )
        except RuntimeError:
            scheme_id = ""
        schemes.append({"name": name, "id": scheme_id, "index": i})

    return schemes


def list_run_destinations() -> list[dict]:
    """List all run destinations in the frontmost workspace.

    Returns:
        List of dicts with keys: name, architecture, platform.
    """
    ensure_xcode_running()
    try:
        names_str = _run_applescript(
            'tell application "Xcode" to get name of every run destination '
            'of front workspace document'
        )
    except RuntimeError:
        return []

    if not names_str:
        return []

    names = [n.strip() for n in names_str.split(",")]

    destinations = []
    for i, name in enumerate(names, 1):
        dest = {"name": name, "index": i}
        for prop in ["architecture", "platform"]:
            try:
                val = _run_applescript(
                    f'tell application "Xcode" to get {prop} of run destination {i} '
                    f'of front workspace document'
                )
                dest[prop] = val
            except RuntimeError:
                dest[prop] = ""
        destinations.append(dest)

    return destinations


def list_projects() -> list[dict]:
    """List projects in the frontmost workspace.

    Returns:
        List of dicts with keys: name, id.
    """
    ensure_xcode_running()
    try:
        names_str = _run_applescript(
            'tell application "Xcode" to get name of every project '
            'of front workspace document'
        )
    except RuntimeError:
        return []

    if not names_str:
        return []

    names = [n.strip() for n in names_str.split(",")]

    projects = []
    for i, name in enumerate(names, 1):
        try:
            proj_id = _run_applescript(
                f'tell application "Xcode" to get id of project {i} '
                f'of front workspace document'
            )
        except RuntimeError:
            proj_id = ""
        projects.append({"name": name, "id": proj_id, "index": i})

    return projects


def list_targets(project: str | None = None) -> list[dict]:
    """List targets in a project.

    Args:
        project: Project name or index. If None, uses the first project.

    Returns:
        List of dicts with keys: name, id.
    """
    ensure_xcode_running()

    if project and project.isdigit():
        proj_ref = f"project {project}"
    elif project:
        proj_ref = f'(first project whose name is "{project}")'
    else:
        proj_ref = "project 1"

    try:
        names_str = _run_applescript(
            f'tell application "Xcode" to get name of every target of '
            f'{proj_ref} of front workspace document'
        )
    except RuntimeError:
        return []

    if not names_str:
        return []

    names = [n.strip() for n in names_str.split(",")]

    targets = []
    for i, name in enumerate(names, 1):
        try:
            target_id = _run_applescript(
                f'tell application "Xcode" to get id of target {i} of '
                f'{proj_ref} of front workspace document'
            )
        except RuntimeError:
            target_id = ""
        targets.append({"name": name, "id": target_id, "index": i})

    return targets


def get_build_settings(target: str | None = None, config: str | None = None) -> dict:
    """Get build settings for a target and configuration.

    Args:
        target: Target name. If None, uses the first target.
        config: Build configuration name (e.g., "Debug", "Release").

    Returns:
        Dict of build setting key-value pairs.
    """
    ensure_xcode_running()

    if target and config:
        try:
            result = _run_applescript(
                f'tell application "Xcode"\n'
                f'  set ws to front workspace document\n'
                f'  set proj to project 1 of ws\n'
                f'  set tgt to (first target of proj whose name is "{target}")\n'
                f'  set cfg to (first build configuration of tgt whose name is "{config}")\n'
                f'  get resolved build settings of cfg\n'
                f'end tell'
            )
            return _parse_build_settings(result)
        except RuntimeError:
            pass

    # Fallback to xcodebuild
    args = ["-showBuildSettings"]
    if target:
        args += ["-target", target]
    if config:
        args += ["-configuration", config]

    try:
        output = _run_xcodebuild(args)
        return _parse_xcodebuild_settings(output)
    except RuntimeError as e:
        return {"error": str(e)}


def _parse_build_settings(raw: str) -> dict:
    """Parse AppleScript build settings output into a dict."""
    settings = {}
    for line in raw.split(","):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            settings[key.strip()] = value.strip()
    return settings


def _parse_xcodebuild_settings(output: str) -> dict:
    """Parse xcodebuild -showBuildSettings output into a dict."""
    settings = {}
    for line in output.splitlines():
        line = line.strip()
        if " = " in line:
            key, _, value = line.partition(" = ")
            settings[key.strip()] = value.strip()
    return settings


def open_workspace(path: str) -> dict:
    """Open a workspace or project file in Xcode.

    Args:
        path: Path to .xcworkspace or .xcodeproj file.

    Returns:
        Dict with result information.
    """
    abs_path = str(Path(path).expanduser().resolve())
    p = Path(abs_path)

    if not p.exists():
        raise RuntimeError(f"File not found: {abs_path}")

    if not (p.suffix in (".xcworkspace", ".xcodeproj")):
        raise RuntimeError(
            f"Unsupported file type: {p.suffix}. "
            "Expected .xcworkspace or .xcodeproj"
        )

    _run_applescript(
        f'tell application "Xcode" to open POSIX file "{abs_path}"'
    )
    ensure_xcode_running()

    return {
        "path": abs_path,
        "name": p.name,
        "message": f"Opened: {p.name}",
    }
