# 1Password Integration Guide

This guide explains how to integrate 1Password with the Conestoga project for secure secrets management.

## Overview

1Password can be used to securely store and retrieve sensitive credentials such as:
- API keys
- Database passwords
- GCP service account keys
- OAuth tokens

## Installation

### 1Password CLI

Install the 1Password CLI tool:

```bash
# macOS
brew install 1password-cli

# Linux
curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
  gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] \
  https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" | \
  tee /etc/apt/sources.list.d/1password.list
apt update && apt install 1password-cli

# Windows
# Download from https://1password.com/downloads/command-line/
```

Verify installation:
```bash
op --version
```

## Authentication Methods

### Method 1: Service Account (Recommended for CI/CD)

1. Create a service account in your 1Password account
2. Generate a service account token
3. Add to your `.env` file:

```bash
OP_SERVICE_ACCOUNT_TOKEN=your_service_account_token
```

### Method 2: 1Password Connect

1. Set up 1Password Connect server
2. Configure in `.env`:

```bash
OP_CONNECT_HOST=https://your-connect-host
OP_CONNECT_TOKEN=your_connect_token
```

### Method 3: Personal Account (Development)

Authenticate manually:

```bash
eval $(op signin)
```

## Usage Examples

### Retrieve a Secret

```bash
# Using service account
export OP_SERVICE_ACCOUNT_TOKEN=your_token
op read "op://vault/item/field"

# Example: Get GCP credentials
op read "op://Production/GCP Service Account/credential" > /tmp/gcp-key.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
```

### Python Integration

```python
import subprocess
import json
from dotenv import load_dotenv

def get_secret(item_path: str) -> str:
    """
    Retrieve a secret from 1Password.
    
    Args:
        item_path: 1Password reference (e.g., "op://vault/item/field")
        
    Returns:
        Secret value
    """
    result = subprocess.run(
        ["op", "read", item_path],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

# Usage
load_dotenv()
api_key = get_secret("op://Development/API Keys/openai")
```

### Injecting Secrets into Environment

```bash
# Run command with secrets injected
op run -- python main.py

# Or in Makefile
run-with-secrets:
	op run -- uv run python main.py
```

## Common Patterns

### GCP Service Account

```bash
# Store GCP key in 1Password
op document create gcp-service-account.json \
  --title "GCP Service Account" \
  --vault Production

# Retrieve and use
op document get "GCP Service Account" > /tmp/gcp-key.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
```

### Environment Variables Template

Create a `.env.template` with 1Password references:

```bash
# .env.template
OPENAI_API_KEY=op://Development/OpenAI/api_key
DATABASE_URL=op://Production/Database/connection_string
GCP_PROJECT_ID=op://Production/GCP/project_id
```

Load with:

```bash
op inject -i .env.template -o .env
```

## Security Best Practices

1. **Never commit secrets** - Keep `.env` in `.gitignore`
2. **Use service accounts** for automation
3. **Rotate credentials** regularly
4. **Limit access** - Use separate vaults for different environments
5. **Audit regularly** - Review access logs in 1Password

## Integration with Make

Add to your Makefile:

```makefile
.PHONY: setup-secrets run-secure

setup-secrets:
	@echo "Setting up secrets from 1Password..."
	@op inject -i .env.template -o .env
	@echo "✅ Secrets configured"

run-secure:
	@echo "Running with 1Password secrets..."
	@op run -- uv run python main.py

clean-secrets:
	@rm -f .env
	@echo "✅ Secrets cleaned"
```

## Troubleshooting

### "not signed in" error
```bash
# Sign in to 1Password
eval $(op signin)
```

### "token expired" error
```bash
# Refresh service account token
# Update OP_SERVICE_ACCOUNT_TOKEN in .env
```

### Permission denied
```bash
# Check vault access permissions in 1Password web interface
# Ensure service account has access to required vaults
```

## References

- [1Password CLI Documentation](https://developer.1password.com/docs/cli)
- [1Password Service Accounts](https://developer.1password.com/docs/service-accounts)
- [1Password Connect](https://developer.1password.com/docs/connect)
