"""
Configuration management for Conestoga.
Handles loading environment variables from multiple sources.
"""

from pathlib import Path

from dotenv import load_dotenv


def load_configuration():
    """
    Load environment variables from .env files.

    Priority (highest to lowest):
    1. System environment variables (already loaded)
    2. Local .env file (in current working directory)
    3. User home .env file (~/.env)

    Note: load_dotenv does not override existing environment variables by default.
    This means we should load from highest priority sources first if we want
    them to take precedence, BUT since system env vars are already there,
    load_dotenv only fills in missing ones.

    However, we want local .env to override home .env if both exist and var is missing from system.
    So we load local .env first, then home .env.
    """
    # 1. Load from local .env
    load_dotenv()

    # 2. Load from user home .env
    home_env = Path.home() / ".env"
    if home_env.exists():
        load_dotenv(home_env)
