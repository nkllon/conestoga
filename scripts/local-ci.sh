#!/bin/bash
set -e

# Fetch API key from 1Password ensuring we get the correct field
echo "Fetching GitGuardian API Key from 1Password..."
GITGUARDIAN_API_KEY=$(op item get "GitGuardian API Token - Personal Access Token" --fields "API Key" --reveal)

if [ -z "$GITGUARDIAN_API_KEY" ]; then
    echo "Error: Could not retrieve GITGUARDIAN_API_KEY from 1Password."
    exit 1
fi

echo "Building local CI Docker image..."
docker build -t conestoga-local-ci -f Dockerfile.local-ci .

echo "Running CI in Docker..."
docker run --rm \
    -e GITGUARDIAN_API_KEY="$GITGUARDIAN_API_KEY" \
    conestoga-local-ci
