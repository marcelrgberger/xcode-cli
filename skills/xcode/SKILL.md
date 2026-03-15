---
name: xcode
description: >-
  Control Xcode from Claude. Build, test, run, clean, archive Xcode projects,
  manage simulators and physical devices, inspect build results.
  Trigger: "/xcode", "xcode build", "build project", "run tests in xcode",
  "clean build", "list simulators", "boot simulator", "xcode schemes",
  "archive app", "build and run", "xcode projekt", "xcode bauen", "xcode testen".
  Use this skill when the user wants to build, test, run, clean, or manage
  Xcode projects, simulators, devices, or inspect build results.
---

# Xcode CLI Skill

Control Xcode from Claude — build, test, run, clean, archive, and manage simulators and devices.

## Prerequisites

The `xcode-cli` command must be installed. If not available, install it automatically:

```bash
which xcode-cli || (cd ${CLAUDE_PLUGIN_ROOT}/agent-harness && python3 -m venv .venv && source .venv/bin/activate && pip install -e . && echo "xcode-cli installed")
```

If a venv already exists, activate it:
```bash
test -f ${CLAUDE_PLUGIN_ROOT}/agent-harness/.venv/bin/activate && source ${CLAUDE_PLUGIN_ROOT}/agent-harness/.venv/bin/activate
```

**System requirements:**
- macOS with Xcode installed
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3.10+

## Command Syntax

| Command | Action |
|---------|--------|
| `/xcode build` | Build the active scheme |
| `/xcode test` | Run tests |
| `/xcode run` | Build and run |
| `/xcode clean` | Clean build |
| `/xcode stop` | Stop running action |
| `/xcode archive` | Create archive |
| `/xcode schemes` | List schemes |
| `/xcode destinations` | List run destinations |
| `/xcode simulators` | List simulators |
| `/xcode devices` | List physical devices |
| `/xcode open <path>` | Open workspace/project |
| `/xcode status` | Show session status |

## CLI Command Reference

**Workspace operations:**
```bash
xcode-cli --json workspace list
xcode-cli --json workspace open "/path/to/Project.xcodeproj"
xcode-cli --json workspace schemes
xcode-cli --json workspace destinations
xcode-cli --json workspace projects
xcode-cli --json workspace targets [--project "ProjectName"]
xcode-cli --json workspace settings [--target "TargetName"] [--config "Debug"]
xcode-cli --json workspace active
```

**Build operations:**
```bash
xcode-cli --json build build [--scheme "MyApp"] [--destination "..."] [--config "Release"]
xcode-cli --json build run [--scheme "MyApp"] [--destination "..."]
xcode-cli --json build test [--scheme "MyApp"] [--destination "..."] [--test-plan "MyTests"]
xcode-cli --json build clean [--scheme "MyApp"]
xcode-cli --json build stop
xcode-cli --json build archive [--scheme "MyApp"] [--output "/path/to/MyApp.xcarchive"]
xcode-cli --json build status
xcode-cli --json build errors
xcode-cli --json build warnings
xcode-cli --json build test-failures
xcode-cli --json build log
```

**Simulator management:**
```bash
xcode-cli --json simulator list [--booted] [--available]
xcode-cli --json simulator boot "iPhone 16"
xcode-cli --json simulator shutdown "iPhone 16"
xcode-cli --json simulator install "iPhone 16" "/path/to/MyApp.app"
xcode-cli --json simulator launch "iPhone 16" "com.example.myapp"
xcode-cli --json simulator screenshot "iPhone 16" ~/Desktop/screenshot.png
xcode-cli --json simulator create "My Sim" "com.apple.CoreSimulator.SimDeviceType.iPhone-16" "com.apple.CoreSimulator.SimRuntime.iOS-18-0"
xcode-cli --json simulator delete "My Sim"
xcode-cli --json simulator types
xcode-cli --json simulator runtimes
```

**Device management:**
```bash
xcode-cli --json device list
xcode-cli --json device info "<udid>"
```

**Editor operations:**
```bash
xcode-cli --json editor file
xcode-cli --json editor text
xcode-cli --json editor selection
xcode-cli --json editor goto 42
xcode-cli --json editor open "/path/to/file.swift"
```

**Session:**
```bash
xcode-cli --json session status
```

## Natural Language -> CLI Mapping

| User says | CLI command |
|-----------|------------|
| "Build the project" | `build build` |
| "Run the app" | `build run` |
| "Run tests" | `build test` |
| "Clean and rebuild" | `build clean` then `build build` |
| "Stop the app" | `build stop` |
| "Show errors" | `build errors` |
| "Any warnings?" | `build warnings` |
| "Which tests failed?" | `build test-failures` |
| "Show the build log" | `build log` |
| "What schemes are there?" | `workspace schemes` |
| "List simulators" | `simulator list --available` |
| "Boot iPhone 16" | `simulator boot "iPhone 16"` |
| "Take a screenshot" | `simulator screenshot "iPhone 16" ~/Desktop/screenshot.png` |
| "Connected devices" | `device list` |
| "Archive for release" | `build archive --scheme "..." --config "Release"` |
| "Open my project" | `workspace open "/path/to/Project.xcodeproj"` |

## Destination Specifiers

Common destination formats for `--destination`:
- iOS Simulator: `"platform=iOS Simulator,name=iPhone 16"`
- iOS Simulator with OS: `"platform=iOS Simulator,name=iPhone 16,OS=18.0"`
- macOS: `"platform=macOS"`
- Any iOS Simulator: `"generic/platform=iOS Simulator"`
- Specific UDID: `"id=<UDID>"`

## Important

- ALWAYS use `--json` for query commands (list, status, errors, warnings, schemes, etc.)
- Xcode launches automatically if not already running
- For build/test, prefer specifying `--scheme` explicitly
- If CLI is not in PATH: `source ${CLAUDE_PLUGIN_ROOT}/agent-harness/.venv/bin/activate`
- Use `--workspace` or `--project` flags when building from command line without Xcode open
