"""Physical device management for Xcode.

Uses xcrun devicectl to list and query connected physical devices.
"""

import json as json_mod

from xcode_cli.utils.xcode_backend import _run_xcrun


def list_devices() -> list[dict]:
    """List connected physical devices.

    Returns:
        List of dicts with keys: name, udid, model, os_version, connection_type.
    """
    try:
        raw = _run_xcrun(["devicectl", "list", "devices", "--json-output", "-"], timeout=30)
        data = json_mod.loads(raw)
        devices = []

        device_list = data.get("result", {}).get("devices", [])
        for dev in device_list:
            props = dev.get("deviceProperties", {})
            hardware = dev.get("hardwareProperties", {})
            conn = dev.get("connectionProperties", {})

            devices.append({
                "name": props.get("name", ""),
                "udid": dev.get("identifier", ""),
                "model": hardware.get("marketingName", hardware.get("productType", "")),
                "os_version": props.get("osVersionNumber", ""),
                "os_build": props.get("osBuildUpdate", ""),
                "platform": hardware.get("platform", ""),
                "architecture": hardware.get("cpuType", {}).get("name", ""),
                "connection_type": conn.get("transportType", ""),
                "is_paired": conn.get("pairingState", "") == "paired",
            })
        return devices

    except RuntimeError:
        # Fallback: try instruments-style listing
        try:
            raw = _run_xcrun(["xctrace", "list", "devices"], timeout=15)
            return _parse_xctrace_devices(raw)
        except RuntimeError:
            return []


def get_device_info(udid: str) -> dict:
    """Get detailed information about a connected device.

    Args:
        udid: Device UDID.

    Returns:
        Dict with device details.
    """
    devices = list_devices()
    for dev in devices:
        if dev.get("udid") == udid:
            return dev

    raise RuntimeError(f"Device not found with UDID: {udid}")


def _parse_xctrace_devices(output: str) -> list[dict]:
    """Parse xctrace list devices output as fallback.

    Args:
        output: Raw xctrace output.

    Returns:
        List of device dicts.
    """
    devices = []
    in_devices_section = False

    for line in output.splitlines():
        stripped = line.strip()

        if stripped.startswith("== Devices =="):
            in_devices_section = True
            continue
        elif stripped.startswith("== Simulators =="):
            in_devices_section = False
            continue

        if in_devices_section and stripped:
            # Format: "Name (OS Version) (UDID)"
            # e.g., "Marcel's iPhone (18.0) (00008110-001234567890)"
            import re
            match = re.match(r"^(.+?)\s+\(([^)]+)\)\s+\(([A-Fa-f0-9-]+)\)$", stripped)
            if match:
                devices.append({
                    "name": match.group(1).strip(),
                    "os_version": match.group(2),
                    "udid": match.group(3),
                    "model": "",
                    "connection_type": "usb",
                })

    return devices
