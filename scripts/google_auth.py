"""One-time Google Calendar authorization.

1. In Google Cloud Console, enable the Google Calendar API and create an OAuth
   client ID of type "Desktop app". Download the JSON.
2. Save it at the path in GOOGLE_CREDENTIALS_PATH (default ./data/google_credentials.json).
3. Run:  python scripts/google_auth.py
   A browser opens; approve access. A token is written to GOOGLE_TOKEN_PATH and
   the agent's calendar tools start working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing deps. Run: pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    creds_path = config.google_credentials_path
    token_path = config.google_token_path

    if not os.path.exists(creds_path):
        print(f"[!] OAuth client secret not found at: {creds_path}")
        print("    Create a Desktop OAuth client in Google Cloud Console and save it there.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)

    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"[✓] Authorized. Token saved to {token_path}. Calendar tools are now live.")


if __name__ == "__main__":
    main()
