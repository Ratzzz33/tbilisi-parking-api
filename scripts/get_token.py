"""scripts/get_token.py — Helper to extract token from browser."""
import sys, json, urllib.request


def get_token_from_chrome(port: int = 9222) -> str:
    """Try to get token from Chrome DevTools Protocol."""
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/json", timeout=3)
        tabs = json.loads(r.read())
        for tab in tabs:
            if tab.get("type") == "page":
                ws = tab.get("webSocketDebuggerUrl", "")
                # We can't easily extract token via CDP this way,
                # but we can navigate and inject
                print(f"Chrome tab: {tab.get('url','')[:60]}")
        return ""
    except Exception as e:
        if "Connection refused" in str(e):
            print("Chrome CDP not available. Start with:")
            print("  google-chrome-stable --headless --remote-debugging-port=9222")
        return ""


if __name__ == "__main__":
    import os
    token = os.environ.get("PARKING_TOKEN", "")
    if not token:
        token = get_token_from_chrome()
    if token:
        print(token)
    else:
        print("PARKING_TOKEN not found. Set it in .env or env var.")
        print("Get it from: https://sso.municipal.gov.ge -> F12 -> localStorage -> token")
        sys.exit(1)
