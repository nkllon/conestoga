# Security & Secrets Management

## Historical Incidents

### Issue #33: Exposed Secrets in Git History (Resolved)

**Incident Date:** 2026-02-09  
**Affected Commit:** `5b40da91c02e0b0926d0f8b7b59cfe512c36cffb`  
**Affected Files:**

* `scripts/verify_token.py` (Deleted)
* `scripts/site_verification_flow.py` (Cleaned in HEAD)

**Description:** (now invalid) tokens were accidentally committed to the repository history.

**Action Taken:**

1. **Verification:** The tokens were extracted and verified against the Cloudflare API.
    * `RlDvjMs...`: Confirmed **INVALID/REVOKED**.
    * `i4vfceb3...`: Confirmed **INVALID**.
2. **Suppression:** The commit `5b40da91c02e0b0926d0f8b7b59cfe512c36cffb` has been added to `.gitleaks.toml` to silence security scanners, as the secrets are no longer valid.

**Status:** Resolved. No further action needed.

> [!NOTE]
> Do NOT use these tokens. They are documented here solely to confirm they have been handled.

## Secret Management

* **Do not verify secrets in git.**
* Use environment variables (e.g., `CLOUDFLARE_TOKEN`) or 1Password.
* Run `gitleaks detect` locally before pushing if uncertain.
