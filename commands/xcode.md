---
name: xcode
description: "Control Xcode — /xcode build, /xcode test, /xcode run, /xcode clean, /xcode simulators, /xcode schemes, /xcode status"
arguments:
  - name: action
    description: "Action: build, test, run, clean, stop, schemes, destinations, simulators, devices, open <path>, status"
    required: false
---

# Xcode CLI — Quick Access

You have access to the Xcode CLI (`xcode-cli`).

## Step 0: Ensure CLI is available

Check if `xcode-cli` is installed. If not, install it automatically:

```bash
which xcode-cli || (cd ${CLAUDE_PLUGIN_ROOT}/agent-harness && python3 -m venv .venv && source .venv/bin/activate && pip install -e . && echo "xcode-cli installed")
```

If a venv already exists, activate it:

```bash
test -f ${CLAUDE_PLUGIN_ROOT}/agent-harness/.venv/bin/activate && source ${CLAUDE_PLUGIN_ROOT}/agent-harness/.venv/bin/activate
```

## Your task

Parse the argument `$ARGUMENTS` and execute the matching action:

### If no argument or "status":
```bash
xcode-cli --json session status
```
Display Xcode status (running, active scheme, destination).

### If "build":
```bash
xcode-cli --json build build
```
Report success/failure, error count, warning count.

### If "test":
```bash
xcode-cli --json build test
```
Report test results, failures.

### If "run":
```bash
xcode-cli --json build run
```
Confirm the app is running.

### If "clean":
```bash
xcode-cli --json build clean
```

### If "stop":
```bash
xcode-cli --json build stop
```

### If "schemes":
```bash
xcode-cli --json workspace schemes
```
Display schemes in a clear list.

### If "destinations":
```bash
xcode-cli --json workspace destinations
```

### If "simulators":
```bash
xcode-cli --json simulator list --available
```
Display available simulators.

### If "devices":
```bash
xcode-cli --json device list
```

### If "open <path>":
```bash
xcode-cli --json workspace open "<path>"
```
Open the workspace/project and show its schemes.

### If "errors":
```bash
xcode-cli --json build errors
```

### If "warnings":
```bash
xcode-cli --json build warnings
```

### If "test-failures":
```bash
xcode-cli --json build test-failures
```

### If "log":
```bash
xcode-cli --json build log
```

### If "archive":
```bash
xcode-cli --json build archive --scheme "<scheme>" --output "<path>"
```

## After opening a workspace

Once a workspace is open, translate the user's natural language into CLI commands:

- Build it → `build build --scheme "..."`
- Run on iPhone → `build run --scheme "..." --destination "platform=iOS Simulator,name=iPhone 16"`
- Run tests → `build test --scheme "..."`
- Clean and rebuild → `build clean --scheme "..."` then `build build --scheme "..."`
- Show me the simulators → `simulator list --available`
- Boot iPhone 16 → `simulator boot "iPhone 16"`
- Take a screenshot → `simulator screenshot "iPhone 16" ~/Desktop/screenshot.png`
- What's the build status? → `build status`
- Show errors → `build errors`
- Archive for release → `build archive --scheme "..." --output ~/Desktop/MyApp.xcarchive`

ALWAYS use `--json` for query commands to get structured output.
