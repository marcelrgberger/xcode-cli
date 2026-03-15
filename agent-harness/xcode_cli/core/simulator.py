"""Simulator management for Xcode.

Uses xcrun simctl for all simulator operations: listing, booting, shutting down,
installing apps, launching apps, taking screenshots, and managing simulator lifecycle.
"""

import json as json_mod
from pathlib import Path

from xcode_cli.utils.xcode_backend import _run_xcrun


def list_simulators() -> list[dict]:
    """List all simulators.

    Returns:
        List of dicts with keys: name, udid, state, runtime, device_type, is_available.
    """
    raw = _run_xcrun(["simctl", "list", "devices", "-j"])
    data = json_mod.loads(raw)

    simulators = []
    devices_map = data.get("devices", {})

    for runtime, devices in devices_map.items():
        # runtime is like "com.apple.CoreSimulator.SimRuntime.iOS-18-0"
        runtime_name = runtime.replace("com.apple.CoreSimulator.SimRuntime.", "").replace("-", " ").replace(".", " ")

        for device in devices:
            simulators.append({
                "name": device.get("name", ""),
                "udid": device.get("udid", ""),
                "state": device.get("state", ""),
                "runtime": runtime_name,
                "runtime_id": runtime,
                "device_type": device.get("deviceTypeIdentifier", ""),
                "is_available": device.get("isAvailable", False),
            })

    return simulators


def boot_simulator(name_or_udid: str) -> dict:
    """Boot a simulator.

    Args:
        name_or_udid: Simulator name or UDID.

    Returns:
        Dict with result information.
    """
    udid = _resolve_simulator_udid(name_or_udid)
    _run_xcrun(["simctl", "boot", udid])
    return {"udid": udid, "message": f"Booted simulator: {name_or_udid}"}


def shutdown_simulator(name_or_udid: str) -> dict:
    """Shutdown a simulator.

    Args:
        name_or_udid: Simulator name or UDID.

    Returns:
        Dict with result information.
    """
    udid = _resolve_simulator_udid(name_or_udid)
    _run_xcrun(["simctl", "shutdown", udid])
    return {"udid": udid, "message": f"Shutdown simulator: {name_or_udid}"}


def install_app(simulator: str, app_path: str) -> dict:
    """Install an app on a simulator.

    Args:
        simulator: Simulator name or UDID.
        app_path: Path to the .app bundle.

    Returns:
        Dict with result information.
    """
    udid = _resolve_simulator_udid(simulator)
    abs_path = str(Path(app_path).expanduser().resolve())

    if not Path(abs_path).exists():
        raise RuntimeError(f"App bundle not found: {abs_path}")

    _run_xcrun(["simctl", "install", udid, abs_path])
    return {
        "udid": udid,
        "app_path": abs_path,
        "message": f"Installed {Path(abs_path).name} on simulator",
    }


def launch_app(simulator: str, bundle_id: str) -> dict:
    """Launch an app on a simulator.

    Args:
        simulator: Simulator name or UDID.
        bundle_id: The app bundle identifier.

    Returns:
        Dict with result information.
    """
    udid = _resolve_simulator_udid(simulator)
    _run_xcrun(["simctl", "launch", udid, bundle_id])
    return {
        "udid": udid,
        "bundle_id": bundle_id,
        "message": f"Launched {bundle_id} on simulator",
    }


def take_screenshot(simulator: str, output_path: str) -> dict:
    """Take a screenshot of a simulator.

    Args:
        simulator: Simulator name or UDID.
        output_path: Path to save the screenshot.

    Returns:
        Dict with result information.
    """
    udid = _resolve_simulator_udid(simulator)
    abs_path = str(Path(output_path).expanduser().resolve())

    # Ensure parent directory exists
    Path(abs_path).parent.mkdir(parents=True, exist_ok=True)

    _run_xcrun(["simctl", "io", udid, "screenshot", abs_path])
    return {
        "udid": udid,
        "screenshot_path": abs_path,
        "message": f"Screenshot saved to: {abs_path}",
    }


def open_simulator() -> dict:
    """Open the Simulator application.

    Returns:
        Dict with result information.
    """
    import subprocess
    subprocess.run(["open", "-a", "Simulator"], check=True, timeout=10)
    return {"message": "Simulator app opened"}


def create_simulator(name: str, device_type: str, runtime: str) -> dict:
    """Create a new simulator.

    Args:
        name: Name for the new simulator.
        device_type: Device type identifier (e.g., "com.apple.CoreSimulator.SimDeviceType.iPhone-16").
        runtime: Runtime identifier (e.g., "com.apple.CoreSimulator.SimRuntime.iOS-18-0").

    Returns:
        Dict with keys: udid, name, message.
    """
    udid = _run_xcrun(["simctl", "create", name, device_type, runtime])
    return {
        "udid": udid.strip(),
        "name": name,
        "device_type": device_type,
        "runtime": runtime,
        "message": f"Created simulator '{name}' with UDID: {udid.strip()}",
    }


def delete_simulator(name_or_udid: str) -> dict:
    """Delete a simulator.

    Args:
        name_or_udid: Simulator name or UDID.

    Returns:
        Dict with result information.
    """
    udid = _resolve_simulator_udid(name_or_udid)
    _run_xcrun(["simctl", "delete", udid])
    return {"udid": udid, "message": f"Deleted simulator: {name_or_udid}"}


def list_device_types() -> list[dict]:
    """List available simulator device types.

    Returns:
        List of dicts with keys: name, identifier.
    """
    raw = _run_xcrun(["simctl", "list", "devicetypes", "-j"])
    data = json_mod.loads(raw)

    types = []
    for dt in data.get("devicetypes", []):
        types.append({
            "name": dt.get("name", ""),
            "identifier": dt.get("identifier", ""),
            "product_family": dt.get("productFamily", ""),
        })
    return types


def list_runtimes() -> list[dict]:
    """List available simulator runtimes.

    Returns:
        List of dicts with keys: name, identifier, version, is_available.
    """
    raw = _run_xcrun(["simctl", "list", "runtimes", "-j"])
    data = json_mod.loads(raw)

    runtimes = []
    for rt in data.get("runtimes", []):
        runtimes.append({
            "name": rt.get("name", ""),
            "identifier": rt.get("identifier", ""),
            "version": rt.get("version", ""),
            "is_available": rt.get("isAvailable", False),
            "build_version": rt.get("buildversion", ""),
        })
    return runtimes


def _resolve_simulator_udid(name_or_udid: str) -> str:
    """Resolve a simulator name to its UDID.

    If the input looks like a UDID (contains hyphens and is 36 chars), returns it directly.
    Otherwise searches for a booted or available simulator with the given name.

    Args:
        name_or_udid: Simulator name or UDID.

    Returns:
        str: The simulator UDID.

    Raises:
        RuntimeError: If no matching simulator is found.
    """
    # Check if it's already a UDID format
    if len(name_or_udid) == 36 and name_or_udid.count("-") == 4:
        return name_or_udid

    # Search by name
    sims = list_simulators()
    matches = [s for s in sims if s["name"].lower() == name_or_udid.lower()]

    if not matches:
        # Try partial match
        matches = [s for s in sims if name_or_udid.lower() in s["name"].lower()]

    if not matches:
        raise RuntimeError(f"No simulator found matching: {name_or_udid}")

    # Prefer booted simulators
    booted = [s for s in matches if s["state"] == "Booted"]
    if booted:
        return booted[0]["udid"]

    # Prefer available simulators
    available = [s for s in matches if s["is_available"]]
    if available:
        return available[0]["udid"]

    return matches[0]["udid"]
