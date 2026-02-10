#!/usr/bin/env python3
import json
import os
import subprocess
import sys

ALLOWED_FILES = {".env", "dar_env.txt"}


def check_security():
    # Run gitleaks
    cmd = [
        "gitleaks",
        "detect",
        "--no-git",
        "--redact",
        "-f",
        "json",
        "-r",
        "leaks.json",
        "--exit-code",
        "0",  # Always exit 0 so we can parse findings
        "-v",
    ]

    print("Running gitleaks...")
    subprocess.run(cmd, check=True)

    # Check if report exists
    if not os.path.exists("leaks.json"):
        print("No leaks report found (maybe no leaks?)")
        return 0

    try:
        with open("leaks.json") as f:
            content = f.read()
            if not content.strip():
                leaks = []
            else:
                leaks = json.loads(content)
    except json.JSONDecodeError:
        print("Failed to parse leaks.json")
        return 1

    real_leaks = []
    for leak in leaks:
        file = leak.get("File")
        if file in ALLOWED_FILES:
            continue
        real_leaks.append(leak)

    if real_leaks:
        print(f"❌ Found {len(real_leaks)} true leaks:")
        for leak in real_leaks:
            print(f"- {leak.get('File')}: {leak.get('RuleID')} (Line {leak.get('StartLine')})")
        return 1
    else:
        print("✅ No leaks found (ignoring allowed files).")
        # Clean up report
        if os.path.exists("leaks.json"):
            os.remove("leaks.json")
        return 0


if __name__ == "__main__":
    sys.exit(check_security())
