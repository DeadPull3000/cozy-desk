import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.google_auth import CREDS_PATH, TOKEN_PATH, SCOPES
from google_auth_oauthlib.flow import InstalledAppFlow

print("Initiating Google OAuth setup...", flush=True)

if not os.path.exists(CREDS_PATH):
    print(f"Error: Missing credentials.json at {CREDS_PATH}", flush=True)
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)

class PromptFormatter:
    def format(self, **kwargs):
        url = kwargs.get("url", "")
        with open("auth_url.txt", "w", encoding="utf-8") as f:
            f.write(url)
        msg = f"\n{'='*60}\nPLEASE OPEN THIS URL IN YOUR BROWSER TO AUTHORIZE:\n{url}\n{'='*60}\n"
        sys.stdout.write(msg)
        sys.stdout.flush()
        return msg

creds = flow.run_local_server(
    port=8085,
    authorization_prompt_message=PromptFormatter(),
    open_browser=True
)

if creds and creds.valid:
    with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())
    print("\n" + "-" * 50, flush=True)
    print("Success! token.json has been generated.", flush=True)
    print("You can now restart your backend and use the 'Sync Classroom' button in the UI.", flush=True)