# Conestoga DevOps Guide

## Deployment Environment

Conestoga is deployed as a containerized application on **Google Cloud Run**.

- **Project ID**: `energration-website-1769745916`
- **Region**: `us-central1` (or nearest available)
- **Service Name**: `conestoga-app` (TBD verify actual)
- **Domain**: `conestoga.nkllon.com`

## CI/CD Pipeline

We use **GitHub Actions** for Continuous Integration and Continuous Deployment.

- **Workflow File**: `.github/workflows/ci.yml`
- **Triggers**: Push to `main`, Pull Requests.
- **Stages**:
    1. **Build**: Sets up Python environment, installs dependencies.
    2. **Lint**: Runs `ruff` for code style and quality checks.
    3. **Test**: Runs `pytest` to verify core logic.
    4. **Deploy** (Main only): Builds Docker image, pushes to Artifact Registry, and deploys to Cloud Run.

## Secrets Management

Sensitive credentials are managed using **1Password** and injected via environment variables.

- **Local Development**: Store `.env` file (git-ignored) with `GEMINI_API_KEY`.
- **Cloud Run**: Secrets are mounted/injected from Google Secret Manager.
- **1Password Use**:
  - Store Cloudflare tokens, GCP Service Account keys, and Gemini API keys in the `Energration` vault.
  - Use `op run --` to inject secrets into local CLI commands when needed.

## Monitoring & Observability

- **Logs**: All application logs (stdout/stderr) are captured by **Cloud Logging**. Filter by `resource.type="cloud_run_revision" AND resource.labels.service_name="conestoga-app"`.
- **Errors**: Critical exceptions are reported to **Cloud Error Reporting**.
- **Performance**: Monitor request latency and instance count in the Cloud Run dashboard.

## Manual Deployment Checklist

1. Ensure `gcloud` CLI is installed and authenticated.
2. Build the image: `docker build -t gcr.io/energration-website-1769745916/conestoga:latest .`
3. Push: `docker push gcr.io/energration-website-1769745916/conestoga:latest`
4. Deploy: `gcloud run deploy conestoga-app --image gcr.io/energration-website-1769745916/conestoga:latest --platform managed`

## Domain Verification (Cloudflare)

- DNS is managed via Cloudflare.
- TXT records are used for domain verification to map the custom domain to Cloud Run.
- Run `scripts/site_verification_flow.py` (with appropriate env vars) to automate TXT record management.
