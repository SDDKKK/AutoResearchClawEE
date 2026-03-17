#!/usr/bin/env python3
"""Web Search — Grok API search.

Usage: python3 web_search.py <query> [--platform <platform>] [--model <model>]

Requires: GROK_API_URL, GROK_API_KEY
"""

import json
import os
import sys
import urllib.request

SEARCH_PROMPT = (
    "Search the web for the following query and return structured results "
    "with title, URL, snippet, and source for each result."
)


def search(query: str, platform: str = "", model: str = "") -> str:
    api_url = os.environ.get("GROK_API_URL")
    api_key = os.environ.get("GROK_API_KEY")
    if not api_url or not api_key:
        return "Error: GROK_API_URL and GROK_API_KEY must be set"

    effective_model = model or os.environ.get("GROK_MODEL", "grok-4-fast")
    full_query = f"{query} (platform: {platform})" if platform else query

    payload = json.dumps(
        {
            "model": effective_model,
            "messages": [
                {"role": "system", "content": SEARCH_PROMPT},
                {"role": "user", "content": full_query},
            ],
            "search_mode": "auto",
        }
    ).encode()

    endpoint = f"{api_url.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: web_search.py <query> [--platform <p>] [--model <m>]",
            file=sys.stderr,
        )
        sys.exit(1)

    args = sys.argv[1:]
    query = args[0]
    platform = ""
    model = ""
    i = 1
    while i < len(args):
        if args[i] == "--platform" and i + 1 < len(args):
            platform = args[i + 1]
            i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        else:
            i += 1

    print(search(query, platform, model))
