#!/usr/bin/env python3
"""
JSON helper script for task.py (replaces jq dependency)

Usage:
  json-helper.py get <file> <key> [default]
  json-helper.py set <file> <key> <value>
  json-helper.py update <file> <json-updates>
  json-helper.py parse <json-string> <key> [default]
"""

import json
import sys


def get_value(file_path, key, default=""):
    """Get value from JSON file"""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        # Support nested keys like "status_history[0].from"
        keys = key.split(".")
        value = data
        for k in keys:
            if "[" in k:
                # Handle array access
                k, idx = k.split("[")
                idx = int(idx.rstrip("]"))
                value = value.get(k, [])[idx]
            else:
                value = value.get(k)
                if value is None:
                    return default

        return str(value) if value is not None else default
    except Exception:
        return default


def set_value(file_path, key, value):
    """Set value in JSON file"""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        data[key] = value

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def update_json(file_path, updates_json):
    """Update JSON file with multiple changes"""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        updates = json.loads(updates_json)
        data.update(updates)

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def parse_string(json_string, key, default=""):
    """Parse JSON string and get value"""
    try:
        data = json.loads(json_string)
        value = data.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        file_path = sys.argv[2]
        key = sys.argv[3]
        default = sys.argv[4] if len(sys.argv) > 4 else ""
        print(get_value(file_path, key, default))

    elif command == "set":
        file_path = sys.argv[2]
        key = sys.argv[3]
        value = sys.argv[4]
        sys.exit(set_value(file_path, key, value))

    elif command == "update":
        file_path = sys.argv[2]
        updates_json = sys.argv[3]
        sys.exit(update_json(file_path, updates_json))

    elif command == "parse":
        json_string = sys.argv[2]
        key = sys.argv[3]
        default = sys.argv[4] if len(sys.argv) > 4 else ""
        print(parse_string(json_string, key, default))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)
