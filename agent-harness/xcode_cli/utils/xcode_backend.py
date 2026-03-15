"""Backend module that wraps osascript, xcodebuild, and xcrun for Xcode."""

import shutil
import subprocess
from pathlib import Path


def _run_applescript(script: str, timeout: int = 30) -> str:
    """Run an AppleScript string via osascript.

    Args:
        script: The AppleScript code to execute.
        timeout: Timeout in seconds. Defaults to 30.

    Returns:
        str: The stdout output from osascript.

    Raises:
        RuntimeError: If the script fails to execute.
    """
    osascript = shutil.which("osascript")
    if not osascript:
        raise RuntimeError(
            "osascript not found. This tool requires macOS with osascript available."
        )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"AppleScript timed out after {timeout} seconds. Script: {script[:200]}..."
        )

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise RuntimeError(
            f"AppleScript execution failed (exit code {result.returncode}): {error_msg}"
        )

    return result.stdout.strip()


def _run_xcodebuild(args: list[str], timeout: int = 300) -> str:
    """Run xcodebuild with the given arguments.

    Args:
        args: List of arguments to pass to xcodebuild.
        timeout: Timeout in seconds. Defaults to 300 (5 minutes).

    Returns:
        str: The stdout output from xcodebuild.

    Raises:
        RuntimeError: If xcodebuild fails.
    """
    xcodebuild = "/usr/bin/xcodebuild"
    if not Path(xcodebuild).exists():
        xcodebuild = shutil.which("xcodebuild")
        if not xcodebuild:
            raise RuntimeError(
                "xcodebuild not found. Install Xcode from the Mac App Store."
            )

    cmd = [xcodebuild] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"xcodebuild timed out after {timeout} seconds. Args: {' '.join(args[:10])}..."
        )

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
        if not error_msg:
            error_msg = "Unknown error"
        raise RuntimeError(
            f"xcodebuild failed (exit code {result.returncode}): {error_msg}"
        )

    return result.stdout.strip()


def _run_xcodebuild_passthrough(args: list[str], timeout: int = 300) -> tuple[str, str, int]:
    """Run xcodebuild and return stdout, stderr, and returncode without raising.

    Useful for build/test commands where we want to parse output regardless of exit code.

    Args:
        args: List of arguments to pass to xcodebuild.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (stdout, stderr, returncode).
    """
    xcodebuild = "/usr/bin/xcodebuild"
    if not Path(xcodebuild).exists():
        xcodebuild = shutil.which("xcodebuild")
        if not xcodebuild:
            raise RuntimeError(
                "xcodebuild not found. Install Xcode from the Mac App Store."
            )

    cmd = [xcodebuild] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"xcodebuild timed out after {timeout} seconds. Args: {' '.join(args[:10])}..."
        )

    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _run_xcrun(args: list[str], timeout: int = 60) -> str:
    """Run xcrun with the given arguments.

    Args:
        args: List of arguments to pass to xcrun.
        timeout: Timeout in seconds. Defaults to 60.

    Returns:
        str: The stdout output from xcrun.

    Raises:
        RuntimeError: If xcrun fails.
    """
    xcrun = "/usr/bin/xcrun"
    if not Path(xcrun).exists():
        xcrun = shutil.which("xcrun")
        if not xcrun:
            raise RuntimeError(
                "xcrun not found. Install Xcode Command Line Tools."
            )

    cmd = [xcrun] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"xcrun timed out after {timeout} seconds. Args: {' '.join(args[:10])}..."
        )

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
        if not error_msg:
            error_msg = "Unknown error"
        raise RuntimeError(
            f"xcrun failed (exit code {result.returncode}): {error_msg}"
        )

    return result.stdout.strip()


def find_xcode() -> str:
    """Check if Xcode is installed and return the application path.

    Returns:
        str: The path to the Xcode application.

    Raises:
        RuntimeError: If Xcode is not installed.
    """
    xcode_paths = [
        Path("/Applications/Xcode.app"),
        Path("/Applications/Xcode-beta.app"),
    ]
    for p in xcode_paths:
        if p.exists():
            return str(p)

    # Try xcode-select
    try:
        result = subprocess.run(
            ["xcode-select", "-p"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            developer_dir = result.stdout.strip()
            # /Applications/Xcode.app/Contents/Developer -> /Applications/Xcode.app
            app_path = Path(developer_dir).parent.parent
            if app_path.exists() and app_path.suffix == ".app":
                return str(app_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    raise RuntimeError(
        "Xcode is not installed. Install it from the Mac App Store: "
        "https://apps.apple.com/app/xcode/id497799835"
    )


def is_xcode_running() -> bool:
    """Check if Xcode is currently running.

    Returns:
        bool: True if Xcode is running, False otherwise.
    """
    try:
        result = _run_applescript(
            'tell application "System Events" to (name of processes) contains "Xcode"'
        )
        return result.strip().lower() == "true"
    except RuntimeError:
        return False


def ensure_xcode_running() -> None:
    """Ensure Xcode is running, launching it if necessary.

    Raises:
        RuntimeError: If Xcode cannot be launched.
    """
    find_xcode()  # Verify Xcode is installed

    if not is_xcode_running():
        try:
            _run_applescript('tell application "Xcode" to activate')
        except RuntimeError as e:
            raise RuntimeError(f"Failed to launch Xcode: {e}")
