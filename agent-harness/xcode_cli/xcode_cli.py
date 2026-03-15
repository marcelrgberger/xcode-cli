"""xcode-cli -- Click-based CLI for Xcode automation.

Main entry point for the CLI harness. Supports both one-shot commands
and an interactive REPL mode (default when no subcommand is given).

This file provides coverage of the Xcode AppleScript/sdef API,
xcodebuild CLI, and xcrun simctl tools.
"""

import json
import sys
from pathlib import Path

import click

from xcode_cli import __version__
from xcode_cli.utils.repl_skin import ReplSkin
from xcode_cli.utils.xcode_backend import (
    _run_applescript,
    _run_xcodebuild,
    _run_xcrun,
    ensure_xcode_running,
    is_xcode_running,
    find_xcode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SessionState:
    """Holds runtime state shared across CLI invocations."""

    def __init__(self):
        self.current_workspace: str | None = None
        self.current_scheme: str | None = None
        self.json_mode: bool = False

    @property
    def workspace_name(self) -> str:
        """Short display name of the current workspace."""
        if self.current_workspace:
            return Path(self.current_workspace).stem
        return ""


pass_state = click.make_pass_decorator(SessionState, ensure=True)


def _output(ctx: click.Context, data: dict):
    """Emit output: JSON when --json is active, otherwise human-readable."""
    state: SessionState = ctx.ensure_object(SessionState)
    if state.json_mode:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if "error" in data:
            click.echo(f"Error: {data['error']}", err=True)
        elif "message" in data:
            click.echo(data["message"])
        elif "rows" in data and "headers" in data:
            skin = ReplSkin("xcode", version=__version__)
            skin.table(data["headers"], data["rows"])
        else:
            for key, value in data.items():
                if isinstance(value, list):
                    click.echo(f"{key}:")
                    for item in value:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                click.echo(f"  {k}: {v}")
                            click.echo()
                        else:
                            click.echo(f"  {item}")
                elif isinstance(value, dict):
                    click.echo(f"{key}:")
                    for k, v in value.items():
                        click.echo(f"  {k}: {v}")
                else:
                    click.echo(f"{key}: {value}")


def _safe_run(func, *args, **kwargs):
    """Run a function and return (result, None) or (None, error_string)."""
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Output results as JSON.")
@click.version_option(version=__version__, prog_name="xcode-cli")
@click.pass_context
def cli(ctx, json_mode):
    """xcode-cli -- Agent-operable CLI for Xcode."""
    state = ctx.ensure_object(SessionState)
    state.json_mode = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


# ===========================================================================
# workspace group
# ===========================================================================

@cli.group()
@click.pass_context
def workspace(ctx):
    """Workspace and project operations."""
    pass


@workspace.command("list")
@click.pass_context
def workspace_list(ctx):
    """List open workspaces."""
    from xcode_cli.core.workspace import list_workspaces
    result, err = _safe_run(list_workspaces)
    if err:
        _output(ctx, {"error": f"Failed to list workspaces: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"workspaces": result, "count": len(result)})
    else:
        if not result:
            click.echo("No workspaces open.")
        else:
            for ws in result:
                loaded = "loaded" if ws.get("loaded") else "not loaded"
                click.echo(f"  {ws['name']} ({loaded})")


@workspace.command("open")
@click.argument("file_path")
@click.pass_context
def workspace_open(ctx, file_path):
    """Open a workspace or project file."""
    from xcode_cli.core.workspace import open_workspace
    result, err = _safe_run(open_workspace, file_path)
    if err:
        _output(ctx, {"error": f"Failed to open workspace: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    state.current_workspace = result.get("name", Path(file_path).stem)
    _output(ctx, result)


@workspace.command("schemes")
@click.pass_context
def workspace_schemes(ctx):
    """List all schemes."""
    from xcode_cli.core.workspace import list_schemes
    result, err = _safe_run(list_schemes)
    if err:
        _output(ctx, {"error": f"Failed to list schemes: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"schemes": result, "count": len(result)})
    else:
        if not result:
            click.echo("No schemes found.")
        else:
            for s in result:
                click.echo(f"  {s['name']}")


@workspace.command("destinations")
@click.pass_context
def workspace_destinations(ctx):
    """List run destinations."""
    from xcode_cli.core.workspace import list_run_destinations
    result, err = _safe_run(list_run_destinations)
    if err:
        _output(ctx, {"error": f"Failed to list destinations: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"destinations": result, "count": len(result)})
    else:
        if not result:
            click.echo("No run destinations found.")
        else:
            for d in result:
                arch = d.get("architecture", "")
                platform = d.get("platform", "")
                extra = f" ({platform}, {arch})" if platform or arch else ""
                click.echo(f"  {d['name']}{extra}")


@workspace.command("projects")
@click.pass_context
def workspace_projects(ctx):
    """List projects in workspace."""
    from xcode_cli.core.workspace import list_projects
    result, err = _safe_run(list_projects)
    if err:
        _output(ctx, {"error": f"Failed to list projects: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"projects": result, "count": len(result)})
    else:
        if not result:
            click.echo("No projects found.")
        else:
            for p in result:
                click.echo(f"  {p['name']}")


@workspace.command("targets")
@click.option("--project", "project_name", default=None,
              help="Project name to list targets from.")
@click.pass_context
def workspace_targets(ctx, project_name):
    """List targets in a project."""
    from xcode_cli.core.workspace import list_targets
    result, err = _safe_run(list_targets, project=project_name)
    if err:
        _output(ctx, {"error": f"Failed to list targets: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"targets": result, "count": len(result)})
    else:
        if not result:
            click.echo("No targets found.")
        else:
            for t in result:
                click.echo(f"  {t['name']}")


@workspace.command("settings")
@click.option("--target", "target_name", default=None,
              help="Target name.")
@click.option("--config", "config_name", default=None,
              help="Build configuration name (e.g., Debug, Release).")
@click.pass_context
def workspace_settings(ctx, target_name, config_name):
    """Show build settings."""
    from xcode_cli.core.workspace import get_build_settings
    result, err = _safe_run(get_build_settings, target=target_name, config=config_name)
    if err:
        _output(ctx, {"error": f"Failed to get build settings: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"build_settings": result, "count": len(result)})
    else:
        for key, value in sorted(result.items()):
            click.echo(f"  {key} = {value}")


@workspace.command("active")
@click.pass_context
def workspace_active(ctx):
    """Show active scheme and run destination."""
    from xcode_cli.core.workspace import get_active_scheme, get_active_run_destination
    scheme, err_s = _safe_run(get_active_scheme)
    dest, err_d = _safe_run(get_active_run_destination)

    data = {}
    if err_s:
        data["scheme_error"] = err_s
    else:
        data["active_scheme"] = scheme or "(none)"
    if err_d:
        data["destination_error"] = err_d
    else:
        data["active_destination"] = dest

    _output(ctx, data)


# ===========================================================================
# build group
# ===========================================================================

@cli.group(name="build")
@click.pass_context
def build_group(ctx):
    """Build operations."""
    pass


@build_group.command("run")
@click.option("--scheme", default=None, help="Scheme name.")
@click.option("--destination", default=None, help="Destination specifier.")
@click.option("--project", default=None, help="Path to .xcodeproj.")
@click.option("--workspace", "ws", default=None, help="Path to .xcworkspace.")
@click.pass_context
def build_run(ctx, scheme, destination, project, ws):
    """Build and run."""
    from xcode_cli.core.build import run
    result, err = _safe_run(run, scheme=scheme, destination=destination,
                            project=project, workspace=ws)
    if err:
        _output(ctx, {"error": f"Failed to run: {err}"})
        return
    _output(ctx, result)


@build_group.command("build")
@click.option("--scheme", default=None, help="Scheme name.")
@click.option("--destination", default=None, help="Destination specifier.")
@click.option("--config", default=None, help="Build configuration.")
@click.option("--project", default=None, help="Path to .xcodeproj.")
@click.option("--workspace", "ws", default=None, help="Path to .xcworkspace.")
@click.pass_context
def build_build(ctx, scheme, destination, config, project, ws):
    """Build only."""
    from xcode_cli.core.build import build
    result, err = _safe_run(build, scheme=scheme, destination=destination,
                            config=config, project=project, workspace=ws)
    if err:
        _output(ctx, {"error": f"Build failed: {err}"})
        return
    _output(ctx, result)


@build_group.command("test")
@click.option("--scheme", default=None, help="Scheme name.")
@click.option("--destination", default=None, help="Destination specifier.")
@click.option("--project", default=None, help="Path to .xcodeproj.")
@click.option("--workspace", "ws", default=None, help="Path to .xcworkspace.")
@click.option("--test-plan", default=None, help="Test plan name.")
@click.pass_context
def build_test(ctx, scheme, destination, project, ws, test_plan):
    """Run tests."""
    from xcode_cli.core.build import test
    result, err = _safe_run(test, scheme=scheme, destination=destination,
                            project=project, workspace=ws, test_plan=test_plan)
    if err:
        _output(ctx, {"error": f"Tests failed: {err}"})
        return
    _output(ctx, result)


@build_group.command("clean")
@click.option("--scheme", default=None, help="Scheme name.")
@click.option("--project", default=None, help="Path to .xcodeproj.")
@click.option("--workspace", "ws", default=None, help="Path to .xcworkspace.")
@click.pass_context
def build_clean(ctx, scheme, project, ws):
    """Clean build."""
    from xcode_cli.core.build import clean
    result, err = _safe_run(clean, scheme=scheme, project=project, workspace=ws)
    if err:
        _output(ctx, {"error": f"Clean failed: {err}"})
        return
    _output(ctx, result)


@build_group.command("stop")
@click.pass_context
def build_stop(ctx):
    """Stop current action."""
    from xcode_cli.core.build import stop
    result, err = _safe_run(stop)
    if err:
        _output(ctx, {"error": f"Failed to stop: {err}"})
        return
    _output(ctx, result)


@build_group.command("archive")
@click.option("--scheme", default=None, help="Scheme name.")
@click.option("--output", "output_path", default=None, help="Archive output path.")
@click.option("--project", default=None, help="Path to .xcodeproj.")
@click.option("--workspace", "ws", default=None, help="Path to .xcworkspace.")
@click.option("--config", default=None, help="Build configuration.")
@click.pass_context
def build_archive(ctx, scheme, output_path, project, ws, config):
    """Create archive."""
    from xcode_cli.core.build import archive
    result, err = _safe_run(archive, scheme=scheme, output=output_path,
                            project=project, workspace=ws, config=config)
    if err:
        _output(ctx, {"error": f"Archive failed: {err}"})
        return
    _output(ctx, result)


@build_group.command("status")
@click.pass_context
def build_status(ctx):
    """Show build status."""
    from xcode_cli.core.build import get_build_status
    result, err = _safe_run(get_build_status)
    if err:
        _output(ctx, {"error": f"Failed to get build status: {err}"})
        return
    _output(ctx, result)


@build_group.command("errors")
@click.pass_context
def build_errors(ctx):
    """Show build errors."""
    from xcode_cli.core.build import get_build_errors
    result, err = _safe_run(get_build_errors)
    if err:
        _output(ctx, {"error": f"Failed to get build errors: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"errors": result, "count": len(result)})
    else:
        if not result:
            click.echo("No build errors.")
        else:
            for e in result:
                click.echo(f"  {e}")


@build_group.command("warnings")
@click.pass_context
def build_warnings(ctx):
    """Show build warnings."""
    from xcode_cli.core.build import get_build_warnings
    result, err = _safe_run(get_build_warnings)
    if err:
        _output(ctx, {"error": f"Failed to get build warnings: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"warnings": result, "count": len(result)})
    else:
        if not result:
            click.echo("No build warnings.")
        else:
            for w in result:
                click.echo(f"  {w}")


@build_group.command("test-failures")
@click.pass_context
def build_test_failures(ctx):
    """Show test failures."""
    from xcode_cli.core.build import get_test_failures
    result, err = _safe_run(get_test_failures)
    if err:
        _output(ctx, {"error": f"Failed to get test failures: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"test_failures": result, "count": len(result)})
    else:
        if not result:
            click.echo("No test failures.")
        else:
            for f in result:
                click.echo(f"  {f}")


@build_group.command("log")
@click.pass_context
def build_log(ctx):
    """Show build log."""
    from xcode_cli.core.build import get_build_log
    result, err = _safe_run(get_build_log)
    if err:
        _output(ctx, {"error": f"Failed to get build log: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"build_log": result})
    else:
        if not result:
            click.echo("No build log available.")
        else:
            click.echo(result)


# ===========================================================================
# simulator group
# ===========================================================================

@cli.group()
@click.pass_context
def simulator(ctx):
    """Simulator management."""
    pass


@simulator.command("list")
@click.option("--booted", is_flag=True, default=False,
              help="Show only booted simulators.")
@click.option("--available", is_flag=True, default=False,
              help="Show only available simulators.")
@click.pass_context
def simulator_list(ctx, booted, available):
    """List simulators."""
    from xcode_cli.core.simulator import list_simulators
    result, err = _safe_run(list_simulators)
    if err:
        _output(ctx, {"error": f"Failed to list simulators: {err}"})
        return

    if booted:
        result = [s for s in result if s.get("state") == "Booted"]
    if available:
        result = [s for s in result if s.get("is_available")]

    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"simulators": result, "count": len(result)})
    else:
        if not result:
            click.echo("No simulators found.")
        else:
            for s in result:
                status = f"[{s['state']}]" if s.get("state") else ""
                avail = "" if s.get("is_available") else " (unavailable)"
                click.echo(f"  {s['name']} {status} - {s.get('runtime', '')}{avail}")
                click.echo(f"    UDID: {s['udid']}")


@simulator.command("boot")
@click.argument("name_or_udid")
@click.pass_context
def simulator_boot(ctx, name_or_udid):
    """Boot a simulator."""
    from xcode_cli.core.simulator import boot_simulator
    result, err = _safe_run(boot_simulator, name_or_udid)
    if err:
        _output(ctx, {"error": f"Failed to boot simulator: {err}"})
        return
    _output(ctx, result)


@simulator.command("shutdown")
@click.argument("name_or_udid")
@click.pass_context
def simulator_shutdown(ctx, name_or_udid):
    """Shutdown a simulator."""
    from xcode_cli.core.simulator import shutdown_simulator
    result, err = _safe_run(shutdown_simulator, name_or_udid)
    if err:
        _output(ctx, {"error": f"Failed to shutdown simulator: {err}"})
        return
    _output(ctx, result)


@simulator.command("install")
@click.argument("simulator_name")
@click.argument("app_path")
@click.pass_context
def simulator_install(ctx, simulator_name, app_path):
    """Install app on simulator."""
    from xcode_cli.core.simulator import install_app
    result, err = _safe_run(install_app, simulator_name, app_path)
    if err:
        _output(ctx, {"error": f"Failed to install app: {err}"})
        return
    _output(ctx, result)


@simulator.command("launch")
@click.argument("simulator_name")
@click.argument("bundle_id")
@click.pass_context
def simulator_launch(ctx, simulator_name, bundle_id):
    """Launch app on simulator."""
    from xcode_cli.core.simulator import launch_app
    result, err = _safe_run(launch_app, simulator_name, bundle_id)
    if err:
        _output(ctx, {"error": f"Failed to launch app: {err}"})
        return
    _output(ctx, result)


@simulator.command("screenshot")
@click.argument("simulator_name")
@click.argument("output_path")
@click.pass_context
def simulator_screenshot(ctx, simulator_name, output_path):
    """Take screenshot of simulator."""
    from xcode_cli.core.simulator import take_screenshot
    result, err = _safe_run(take_screenshot, simulator_name, output_path)
    if err:
        _output(ctx, {"error": f"Failed to take screenshot: {err}"})
        return
    _output(ctx, result)


@simulator.command("create")
@click.argument("name")
@click.argument("device_type")
@click.argument("runtime")
@click.pass_context
def simulator_create(ctx, name, device_type, runtime):
    """Create a new simulator."""
    from xcode_cli.core.simulator import create_simulator
    result, err = _safe_run(create_simulator, name, device_type, runtime)
    if err:
        _output(ctx, {"error": f"Failed to create simulator: {err}"})
        return
    _output(ctx, result)


@simulator.command("delete")
@click.argument("name_or_udid")
@click.pass_context
def simulator_delete(ctx, name_or_udid):
    """Delete a simulator."""
    from xcode_cli.core.simulator import delete_simulator
    result, err = _safe_run(delete_simulator, name_or_udid)
    if err:
        _output(ctx, {"error": f"Failed to delete simulator: {err}"})
        return
    _output(ctx, result)


@simulator.command("types")
@click.pass_context
def simulator_types(ctx):
    """List available device types."""
    from xcode_cli.core.simulator import list_device_types
    result, err = _safe_run(list_device_types)
    if err:
        _output(ctx, {"error": f"Failed to list device types: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"device_types": result, "count": len(result)})
    else:
        if not result:
            click.echo("No device types found.")
        else:
            for dt in result:
                family = f" ({dt['product_family']})" if dt.get("product_family") else ""
                click.echo(f"  {dt['name']}{family}")
                click.echo(f"    {dt['identifier']}")


@simulator.command("runtimes")
@click.pass_context
def simulator_runtimes(ctx):
    """List available runtimes."""
    from xcode_cli.core.simulator import list_runtimes
    result, err = _safe_run(list_runtimes)
    if err:
        _output(ctx, {"error": f"Failed to list runtimes: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"runtimes": result, "count": len(result)})
    else:
        if not result:
            click.echo("No runtimes found.")
        else:
            for rt in result:
                avail = "" if rt.get("is_available") else " (unavailable)"
                click.echo(f"  {rt['name']} ({rt['version']}){avail}")
                click.echo(f"    {rt['identifier']}")


# ===========================================================================
# device group
# ===========================================================================

@cli.group()
@click.pass_context
def device(ctx):
    """Physical device management."""
    pass


@device.command("list")
@click.pass_context
def device_list(ctx):
    """List connected devices."""
    from xcode_cli.core.devices import list_devices
    result, err = _safe_run(list_devices)
    if err:
        _output(ctx, {"error": f"Failed to list devices: {err}"})
        return
    state = ctx.ensure_object(SessionState)
    if state.json_mode:
        _output(ctx, {"devices": result, "count": len(result)})
    else:
        if not result:
            click.echo("No connected devices found.")
        else:
            for dev in result:
                model = f" ({dev['model']})" if dev.get("model") else ""
                click.echo(f"  {dev['name']}{model}")
                click.echo(f"    UDID: {dev['udid']}")
                click.echo(f"    OS: {dev.get('os_version', 'unknown')}")


@device.command("info")
@click.argument("udid")
@click.pass_context
def device_info(ctx, udid):
    """Get device details."""
    from xcode_cli.core.devices import get_device_info
    result, err = _safe_run(get_device_info, udid)
    if err:
        _output(ctx, {"error": f"Failed to get device info: {err}"})
        return
    _output(ctx, result)


# ===========================================================================
# editor group
# ===========================================================================

@cli.group()
@click.pass_context
def editor(ctx):
    """Editor operations."""
    pass


@editor.command("file")
@click.pass_context
def editor_file(ctx):
    """Get current file name."""
    from xcode_cli.core.editor import get_current_file
    result, err = _safe_run(get_current_file)
    if err:
        _output(ctx, {"error": f"Failed to get current file: {err}"})
        return
    _output(ctx, result)


@editor.command("text")
@click.pass_context
def editor_text(ctx):
    """Get document text."""
    from xcode_cli.core.editor import get_document_text
    result, err = _safe_run(get_document_text)
    if err:
        _output(ctx, {"error": f"Failed to get document text: {err}"})
        return
    _output(ctx, result)


@editor.command("selection")
@click.pass_context
def editor_selection(ctx):
    """Get selected text."""
    from xcode_cli.core.editor import get_selected_text
    result, err = _safe_run(get_selected_text)
    if err:
        _output(ctx, {"error": f"Failed to get selected text: {err}"})
        return
    _output(ctx, result)


@editor.command("goto")
@click.argument("line_number", type=int)
@click.pass_context
def editor_goto(ctx, line_number):
    """Go to line number."""
    from xcode_cli.core.editor import go_to_line
    result, err = _safe_run(go_to_line, line_number)
    if err:
        _output(ctx, {"error": f"Failed to go to line: {err}"})
        return
    _output(ctx, result)


@editor.command("open")
@click.argument("file_path")
@click.pass_context
def editor_open(ctx, file_path):
    """Open file in Xcode."""
    from xcode_cli.core.editor import open_file
    result, err = _safe_run(open_file, file_path)
    if err:
        _output(ctx, {"error": f"Failed to open file: {err}"})
        return
    _output(ctx, result)


# ===========================================================================
# session group
# ===========================================================================

@cli.group()
@click.pass_context
def session(ctx):
    """Session management."""
    pass


@session.command("status")
@click.pass_context
def session_status(ctx):
    """Show session status."""
    state = ctx.ensure_object(SessionState)

    data = {
        "workspace": state.current_workspace or "(none)",
        "scheme": state.current_scheme or "(none)",
        "xcode_running": is_xcode_running(),
        "json_mode": state.json_mode,
    }

    # Try to get live info from Xcode
    if is_xcode_running():
        try:
            scheme = _run_applescript(
                'tell application "Xcode" to get name of active scheme '
                'of front workspace document'
            )
            data["live_active_scheme"] = scheme
        except RuntimeError:
            pass

        try:
            dest = _run_applescript(
                'tell application "Xcode" to get name of active run destination '
                'of front workspace document'
            )
            data["live_active_destination"] = dest
        except RuntimeError:
            pass

    try:
        xcode_path = find_xcode()
        data["xcode_path"] = xcode_path
    except RuntimeError:
        data["xcode_path"] = "(not found)"

    _output(ctx, data)


# ===========================================================================
# REPL
# ===========================================================================

_REPL_HELP = {
    # workspace
    "workspace list":            "List open workspaces",
    "workspace open":            "Open workspace/project <file_path>",
    "workspace schemes":         "List schemes",
    "workspace destinations":    "List run destinations",
    "workspace projects":        "List projects",
    "workspace targets":         "List targets [--project P]",
    "workspace settings":        "Show build settings [--target T] [--config C]",
    "workspace active":          "Show active scheme + destination",
    # build
    "build run":                 "Build and run [--scheme S] [--destination D]",
    "build build":               "Build only [--scheme S] [--destination D] [--config C]",
    "build test":                "Run tests [--scheme S] [--destination D] [--test-plan P]",
    "build clean":               "Clean build [--scheme S]",
    "build stop":                "Stop current action",
    "build archive":             "Create archive [--scheme S] [--output O]",
    "build status":              "Show build status",
    "build errors":              "Show build errors",
    "build warnings":            "Show build warnings",
    "build test-failures":       "Show test failures",
    "build log":                 "Show build log",
    # simulator
    "simulator list":            "List simulators [--booted] [--available]",
    "simulator boot":            "Boot simulator <name_or_udid>",
    "simulator shutdown":        "Shutdown simulator <name_or_udid>",
    "simulator install":         "Install app <simulator> <app_path>",
    "simulator launch":          "Launch app <simulator> <bundle_id>",
    "simulator screenshot":      "Take screenshot <simulator> <output>",
    "simulator create":          "Create simulator <name> <device_type> <runtime>",
    "simulator delete":          "Delete simulator <name_or_udid>",
    "simulator types":           "List device types",
    "simulator runtimes":        "List runtimes",
    # device
    "device list":               "List connected devices",
    "device info":               "Device details <udid>",
    # editor
    "editor file":               "Current file name",
    "editor text":               "Get document text",
    "editor selection":          "Get selected text",
    "editor goto":               "Go to line <number>",
    "editor open":               "Open file <path>",
    # session
    "session status":            "Show session status",
    # misc
    "help":                      "Show this help message",
    "quit / exit":               "Exit the REPL",
}


def _tokenize_input(raw: str) -> list[str]:
    """Split user input respecting quoted strings."""
    import shlex
    try:
        return shlex.split(raw)
    except ValueError:
        return raw.split()


def _run_repl(ctx: click.Context):
    """Run the interactive REPL loop."""
    state = ctx.ensure_object(SessionState)
    skin = ReplSkin("xcode", version=__version__)

    skin.print_banner()

    pt_session = skin.create_prompt_session()

    while True:
        ws_name = state.workspace_name
        try:
            if not ws_name and is_xcode_running():
                try:
                    live_ws = _run_applescript(
                        'tell application "Xcode" to get name of front workspace document'
                    )
                    if live_ws:
                        state.current_workspace = live_ws
                        ws_name = live_ws
                except RuntimeError:
                    pass
        except Exception:
            pass

        try:
            user_input = skin.get_input(
                pt_session,
                project_name=ws_name,
            )
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not user_input:
            continue

        lowered = user_input.strip().lower()
        if lowered in ("quit", "exit", "q"):
            skin.print_goodbye()
            break

        if lowered in ("help", "?"):
            skin.help(_REPL_HELP)
            continue

        tokens = _tokenize_input(user_input)
        if not tokens:
            continue

        args = list(tokens)
        if state.json_mode and "--json" not in args:
            args = ["--json"] + args

        try:
            cli.main(
                args=args,
                prog_name="xcode-cli",
                standalone_mode=False,
                **{"obj": state},
            )
        except click.exceptions.UsageError as exc:
            skin.error(str(exc))
            skin.hint("Type 'help' to see available commands.")
        except click.exceptions.Abort:
            skin.warning("Command aborted.")
        except SystemExit:
            pass
        except Exception as exc:
            skin.error(f"Unexpected error: {exc}")


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    """Entry point for setup.py console_scripts."""
    cli(obj=SessionState())


if __name__ == "__main__":
    main()
