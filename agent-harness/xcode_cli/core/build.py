"""Build operations for Xcode.

Uses xcodebuild for build/test/clean/archive operations (more reliable output).
Uses AppleScript for build status, errors, and warnings from scheme action results.
"""

import re

from xcode_cli.utils.xcode_backend import (
    _run_applescript,
    _run_xcodebuild,
    _run_xcodebuild_passthrough,
    ensure_xcode_running,
)


def build(scheme: str | None = None, destination: str | None = None,
          config: str | None = None, project: str | None = None,
          workspace: str | None = None) -> dict:
    """Build the project via xcodebuild.

    Args:
        scheme: Scheme name. If None, uses the active scheme.
        destination: Destination specifier (e.g., "platform=iOS Simulator,name=iPhone 16").
        config: Build configuration (e.g., "Debug", "Release").
        project: Path to .xcodeproj file.
        workspace: Path to .xcworkspace file.

    Returns:
        Dict with keys: success, output, errors, warnings.
    """
    args = ["build"]

    if workspace:
        args += ["-workspace", workspace]
    elif project:
        args += ["-project", project]

    if scheme:
        args += ["-scheme", scheme]
    if destination:
        args += ["-destination", destination]
    if config:
        args += ["-configuration", config]

    stdout, stderr, returncode = _run_xcodebuild_passthrough(args, timeout=600)

    errors = _extract_errors(stdout + "\n" + stderr)
    warnings = _extract_warnings(stdout + "\n" + stderr)

    return {
        "success": returncode == 0,
        "return_code": returncode,
        "errors": errors,
        "error_count": len(errors),
        "warnings": warnings,
        "warning_count": len(warnings),
        "output": stdout[-2000:] if len(stdout) > 2000 else stdout,
    }


def clean(scheme: str | None = None, project: str | None = None,
          workspace: str | None = None) -> dict:
    """Clean the build via xcodebuild.

    Args:
        scheme: Scheme name.
        project: Path to .xcodeproj file.
        workspace: Path to .xcworkspace file.

    Returns:
        Dict with result information.
    """
    args = ["clean"]

    if workspace:
        args += ["-workspace", workspace]
    elif project:
        args += ["-project", project]

    if scheme:
        args += ["-scheme", scheme]

    stdout, stderr, returncode = _run_xcodebuild_passthrough(args, timeout=120)

    return {
        "success": returncode == 0,
        "return_code": returncode,
        "output": stdout[-1000:] if len(stdout) > 1000 else stdout,
        "message": "Clean succeeded" if returncode == 0 else "Clean failed",
    }


def run(scheme: str | None = None, destination: str | None = None,
        project: str | None = None, workspace: str | None = None) -> dict:
    """Build and run via AppleScript (launches in Xcode).

    Args:
        scheme: Scheme name.
        destination: Destination specifier.
        project: Path to .xcodeproj.
        workspace: Path to .xcworkspace.

    Returns:
        Dict with result information.
    """
    ensure_xcode_running()

    # Set scheme if specified
    if scheme:
        try:
            _run_applescript(
                f'tell application "Xcode"\n'
                f'  set ws to front workspace document\n'
                f'  repeat with s in schemes of ws\n'
                f'    if name of s is "{scheme}" then\n'
                f'      set active scheme of ws to s\n'
                f'      exit repeat\n'
                f'    end if\n'
                f'  end repeat\n'
                f'end tell'
            )
        except RuntimeError:
            pass

    # Run via AppleScript
    _run_applescript(
        'tell application "Xcode" to run front workspace document'
    )

    return {
        "message": f"Running scheme: {scheme or '(active)'}",
        "scheme": scheme or "(active)",
    }


def test(scheme: str | None = None, destination: str | None = None,
         project: str | None = None, workspace: str | None = None,
         test_plan: str | None = None) -> dict:
    """Run tests via xcodebuild.

    Args:
        scheme: Scheme name.
        destination: Destination specifier.
        project: Path to .xcodeproj.
        workspace: Path to .xcworkspace.
        test_plan: Name of the test plan.

    Returns:
        Dict with keys: success, output, test_failures, error_count.
    """
    args = ["test"]

    if workspace:
        args += ["-workspace", workspace]
    elif project:
        args += ["-project", project]

    if scheme:
        args += ["-scheme", scheme]
    if destination:
        args += ["-destination", destination]
    if test_plan:
        args += ["-testPlan", test_plan]

    stdout, stderr, returncode = _run_xcodebuild_passthrough(args, timeout=600)

    full_output = stdout + "\n" + stderr
    failures = _extract_test_failures(full_output)
    errors = _extract_errors(full_output)

    return {
        "success": returncode == 0,
        "return_code": returncode,
        "test_failures": failures,
        "failure_count": len(failures),
        "errors": errors,
        "error_count": len(errors),
        "output": stdout[-2000:] if len(stdout) > 2000 else stdout,
        "message": "Tests passed" if returncode == 0 else f"Tests failed ({len(failures)} failures)",
    }


def stop() -> dict:
    """Stop the currently running action in Xcode.

    Returns:
        Dict with result information.
    """
    ensure_xcode_running()
    _run_applescript(
        'tell application "Xcode" to stop front workspace document'
    )
    return {"message": "Stopped running action"}


def archive(scheme: str | None = None, output: str | None = None,
            project: str | None = None, workspace: str | None = None,
            config: str | None = None) -> dict:
    """Create an archive via xcodebuild.

    Args:
        scheme: Scheme name.
        output: Output path for the archive (.xcarchive).
        project: Path to .xcodeproj.
        workspace: Path to .xcworkspace.
        config: Build configuration.

    Returns:
        Dict with result information.
    """
    args = ["archive"]

    if workspace:
        args += ["-workspace", workspace]
    elif project:
        args += ["-project", project]

    if scheme:
        args += ["-scheme", scheme]
    if config:
        args += ["-configuration", config]
    if output:
        args += ["-archivePath", output]

    stdout, stderr, returncode = _run_xcodebuild_passthrough(args, timeout=600)

    return {
        "success": returncode == 0,
        "return_code": returncode,
        "archive_path": output or "",
        "output": stdout[-2000:] if len(stdout) > 2000 else stdout,
        "message": "Archive succeeded" if returncode == 0 else "Archive failed",
    }


def get_build_status() -> dict:
    """Get the current build status via AppleScript scheme action result.

    Returns:
        Dict with keys: status, completed, error_message.
        Status values: not yet started, running, cancelled, failed, error occurred, succeeded.
    """
    ensure_xcode_running()
    result = {}

    try:
        status = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get status of ar\n'
            'end tell'
        )
        result["status"] = status
    except RuntimeError:
        result["status"] = "unknown"

    try:
        completed = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get completed of ar\n'
            'end tell'
        )
        result["completed"] = completed.lower() == "true"
    except RuntimeError:
        result["completed"] = False

    try:
        error_msg = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get error message of ar\n'
            'end tell'
        )
        result["error_message"] = error_msg if error_msg != "missing value" else ""
    except RuntimeError:
        result["error_message"] = ""

    return result


def get_build_errors() -> list[str]:
    """Get build errors from the last scheme action result.

    Returns:
        List of error strings.
    """
    ensure_xcode_running()
    try:
        raw = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get build errors of ar\n'
            'end tell'
        )
        if raw and raw != "missing value":
            return [e.strip() for e in raw.split(",") if e.strip()]
    except RuntimeError:
        pass
    return []


def get_build_warnings() -> list[str]:
    """Get build warnings from the last scheme action result.

    Returns:
        List of warning strings.
    """
    ensure_xcode_running()
    try:
        raw = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get build warnings of ar\n'
            'end tell'
        )
        if raw and raw != "missing value":
            return [w.strip() for w in raw.split(",") if w.strip()]
    except RuntimeError:
        pass
    return []


def get_test_failures() -> list[str]:
    """Get test failures from the last scheme action result.

    Returns:
        List of test failure strings.
    """
    ensure_xcode_running()
    try:
        raw = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get test failures of ar\n'
            'end tell'
        )
        if raw and raw != "missing value":
            return [f.strip() for f in raw.split(",") if f.strip()]
    except RuntimeError:
        pass
    return []


def get_build_log() -> str:
    """Get the build log from the last scheme action result.

    Returns:
        str: The build log text.
    """
    ensure_xcode_running()
    try:
        raw = _run_applescript(
            'tell application "Xcode"\n'
            '  set ws to front workspace document\n'
            '  set ar to last scheme action result of ws\n'
            '  get build log of ar\n'
            'end tell'
        )
        if raw and raw != "missing value":
            return raw
    except RuntimeError:
        pass
    return ""


def _extract_errors(output: str) -> list[str]:
    """Extract error lines from xcodebuild output.

    Args:
        output: Raw xcodebuild output.

    Returns:
        List of error message strings.
    """
    errors = []
    for line in output.splitlines():
        stripped = line.strip()
        if ": error:" in stripped:
            errors.append(stripped)
        elif stripped.startswith("error:"):
            errors.append(stripped)
    return errors


def _extract_warnings(output: str) -> list[str]:
    """Extract warning lines from xcodebuild output.

    Args:
        output: Raw xcodebuild output.

    Returns:
        List of warning message strings.
    """
    warnings = []
    for line in output.splitlines():
        stripped = line.strip()
        if ": warning:" in stripped:
            warnings.append(stripped)
        elif stripped.startswith("warning:"):
            warnings.append(stripped)
    return warnings


def _extract_test_failures(output: str) -> list[str]:
    """Extract test failure lines from xcodebuild test output.

    Args:
        output: Raw xcodebuild output.

    Returns:
        List of test failure description strings.
    """
    failures = []
    # Match patterns like: "TestClassName.testMethodName, ... failed"
    # or "Test Case '-[TestClass testMethod]' failed"
    for line in output.splitlines():
        stripped = line.strip()
        if "failed" in stripped.lower() and ("Test Case" in stripped or "test" in stripped.lower()):
            if re.search(r"(Test Case|test\w+).*failed", stripped, re.IGNORECASE):
                failures.append(stripped)
    return failures
