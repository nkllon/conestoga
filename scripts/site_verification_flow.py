#!/usr/bin/env python3
import os
import sys
import time

import google.auth
import google.auth.transport.requests
import requests
from configure_cloudflare import configure_dns

# Config
DOMAIN = "conestoga.nkllon.com"
CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_TOKEN")
if not CLOUDFLARE_TOKEN:
    raise ValueError("CLOUDFLARE_TOKEN environment variable not set")
CLOUD_RUN_SERVICE = "conestoga"
PROJECT_ID = "gen-lang-client-0128452200"
REGION = "us-central1"


def get_authorized_session():
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/siteverification"]
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Bearer {credentials.token}", "x-goog-user-project": PROJECT_ID}
    )
    return session


def get_verification_token(session):
    print(f"🔑 Requesting verification token for {DOMAIN}...")
    resp = session.post(
        "https://www.googleapis.com/siteVerification/v1/token",
        json={
            "site": {"identifier": DOMAIN, "type": "INET_DOMAIN"},
            "verificationMethod": "DNS_TXT",
        },
    )
    if resp.status_code != 200:
        print(f"❌ Failed to get token: {resp.text}")
        sys.exit(1)

    return resp.json()["token"]


def verify_ownership(session, token):
    print("✨ Verifying ownership now...")
    resp = session.post(
        "https://www.googleapis.com/siteVerification/v1/webResource",
        json={"site": {"identifier": DOMAIN, "type": "INET_DOMAIN"}},
        params={"verificationMethod": "DNS_TXT"},
    )

    if resp.status_code == 200:
        print("✅ Domain verified successfully!")
        return True
    else:
        print(f"❌ Verification failed: {resp.text}")
        return False


def main():
    session = get_authorized_session()

    # 1. Get Token
    txt_record = get_verification_token(session)
    print(f"📝 Got TXT record: {txt_record}")

    # Format: google-site-verification=...
    # We add this to the root domain presumably, or the subdomain?
    # For INET_DOMAIN "conestoga.nkllon.com", we should put the TXT on "conestoga.nkllon.com".

    # 2. Add to Cloudflare
    print("☁️ Adding to Cloudflare...")
    configure_dns(CLOUDFLARE_TOKEN, "nkllon.com", "conestoga", txt_record, "TXT")

    print("⏳ Waiting 10s for propagation...")
    time.sleep(10)

    # 3. Verify
    if verify_ownership(session, txt_record):
        pass
    else:
        print(
            "⚠️ Verification API returned error, but we might proceed to mapping "
            "anyway as it might have worked/be async."
        )


if __name__ == "__main__":
    main()
