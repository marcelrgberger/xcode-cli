"""Editor and document operations for Xcode.

Uses AppleScript to interact with Xcode's text document model:
getting current file, selected text, document text, navigating to lines,
and opening files.
"""

from xcode_cli.utils.xcode_backend import (
    _run_applescript,
    ensure_xcode_running,
)


def get_current_file() -> dict:
    """Get the name and path of the currently active file in Xcode.

    Returns:
        Dict with keys: name, path.
    """
    ensure_xcode_running()

    result = {}
    try:
        name = _run_applescript(
            'tell application "Xcode" to get name of front document'
        )
        result["name"] = name
    except RuntimeError:
        result["name"] = ""

    try:
        path = _run_applescript(
            'tell application "Xcode" to get path of front document'
        )
        result["path"] = path
    except RuntimeError:
        result["path"] = ""

    return result


def get_selected_text() -> dict:
    """Get the currently selected text in the active Xcode editor.

    Returns:
        Dict with keys: text, start, end.
    """
    ensure_xcode_running()

    result = {}
    try:
        text = _run_applescript(
            'tell application "Xcode"\n'
            '  set doc to front document\n'
            '  set sel to selected character range of doc\n'
            '  set selText to text of sel\n'
            '  return selText\n'
            'end tell'
        )
        result["text"] = text
    except RuntimeError:
        result["text"] = ""

    try:
        range_info = _run_applescript(
            'tell application "Xcode"\n'
            '  set doc to front document\n'
            '  set sel to selected character range of doc\n'
            '  return (offset of sel) & "," & (length of sel)\n'
            'end tell'
        )
        parts = range_info.split(",")
        if len(parts) == 2:
            result["offset"] = parts[0].strip()
            result["length"] = parts[1].strip()
    except RuntimeError:
        result["offset"] = ""
        result["length"] = ""

    return result


def get_document_text() -> dict:
    """Get the full text of the frontmost document in Xcode.

    Returns:
        Dict with keys: text, name.
    """
    ensure_xcode_running()

    result = {}
    try:
        name = _run_applescript(
            'tell application "Xcode" to get name of front document'
        )
        result["name"] = name
    except RuntimeError:
        result["name"] = ""

    try:
        text = _run_applescript(
            'tell application "Xcode" to get text of front document',
            timeout=60,
        )
        result["text"] = text
    except RuntimeError:
        result["text"] = ""

    return result


def go_to_line(line_number: int) -> dict:
    """Navigate to a specific line number in the active editor.

    Uses the AppleScript 'hack' command to jump to a line.

    Args:
        line_number: The line number to navigate to.

    Returns:
        Dict with result information.
    """
    ensure_xcode_running()

    if line_number < 1:
        raise RuntimeError("Line number must be 1 or greater")

    # The 'hack' command in Xcode's sdef navigates to a line
    _run_applescript(
        f'tell application "Xcode"\n'
        f'  set doc to front document\n'
        f'  set selected paragraph range of doc to paragraph {line_number} of doc\n'
        f'end tell'
    )

    return {
        "line": line_number,
        "message": f"Navigated to line {line_number}",
    }


def open_file(path: str) -> dict:
    """Open a file in Xcode.

    Args:
        path: Path to the file to open.

    Returns:
        Dict with result information.
    """
    from pathlib import Path as PathLib
    abs_path = str(PathLib(path).expanduser().resolve())

    if not PathLib(abs_path).exists():
        raise RuntimeError(f"File not found: {abs_path}")

    ensure_xcode_running()

    _run_applescript(
        f'tell application "Xcode" to open POSIX file "{abs_path}"'
    )

    return {
        "path": abs_path,
        "name": PathLib(abs_path).name,
        "message": f"Opened: {PathLib(abs_path).name}",
    }
