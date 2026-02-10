import json
import os
import sys

import requests


def configure_dns(token, domain, record_name, target, record_type="CNAME"):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Get Zone ID
    print(f"🔍 Looking up zone for {domain}...")
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={domain}", headers=headers
    )
    if resp.status_code != 200:
        print(f"❌ Failed to list zones: {resp.text}")
        sys.exit(1)

    zones = resp.json().get("result", [])
    if not zones:
        print(f"❌ Zone {domain} not found.")
        sys.exit(1)

    zone_id = zones[0]["id"]
    print(f"✅ Found Zone ID: {zone_id}")

    # 2. Check existing record
    full_record_name = f"{record_name}.{domain}"
    print(f"🔍 Checking for existing record: {full_record_name}...")
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={full_record_name}&type={record_type}",
        headers=headers,
    )

    existing_records = resp.json().get("result", [])

    data = {
        "type": record_type,
        "name": record_name,
        "content": target,
        "ttl": 1,  # Auto
    }

    if record_type == "CNAME":
        data["proxied"] = True

    if existing_records:
        record_id = existing_records[0]["id"]
        print(f"🔄 Updating existing record {record_id}...")
        resp = requests.put(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
            headers=headers,
            json=data,
        )
    else:
        print("➕ Creating new record...")
        resp = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
            headers=headers,
            json=data,
        )

    if resp.status_code in [200, 201]:
        print(f"✅ Success! {full_record_name} -> {target}")
        print(json.dumps(resp.json().get("result"), indent=2))
    else:
        print(f"❌ Failed to configure record: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    token = os.environ.get("CLOUDFLARE_TOKEN")
    if not token:
        # Fallback to 1Password
        try:
            import subprocess

            print("🔐 Attempting to fetch CLOUDFLARE_TOKEN from 1Password...")
            result = subprocess.run(
                ["op", "read", "op://energration/v5ga632uvvehpygjltskllkiyy/credential"],
                capture_output=True,
                text=True,
                check=True,
            )
            token = result.stdout.strip()
            print("✓ Retrieved token from 1Password")
        except Exception:
            pass

    if not token:
        print(
            "Error: CLOUDFLARE_TOKEN environment variable not set "
            "and could not be retrieved from 1Password"
        )
        sys.exit(1)

    if len(sys.argv) < 4:
        print("Usage: python configure_cloudflare.py <domain> <record> <target> [type]")
        sys.exit(1)

    r_type = sys.argv[4] if len(sys.argv) > 4 else "CNAME"
    configure_dns(token, sys.argv[1], sys.argv[2], sys.argv[3], r_type)
