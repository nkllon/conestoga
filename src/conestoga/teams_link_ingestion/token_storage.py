"""
Token Storage Module

Placeholder implementation for OAuth token persistence.
"""


class TokenStorage:
    """
    Placeholder implementation of TokenStorage.

    The original implementation was expected to be imported from
    ``scripts.teams_link_ingestion.token_storage``, but that module is
    not available in this codebase. This stub is provided to avoid
    import errors; any concrete behavior should be implemented here.
    """

    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "TokenStorage is a stub implementation. "
            "Provide a concrete implementation in "
            "src/conestoga/teams_link_ingestion/token_storage.py."
        )


__all__ = ["TokenStorage"]

