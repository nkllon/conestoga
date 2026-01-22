"""
Heuristic audit helper. When enabled (e.g., via env flag), runs lightweight checks
and, if LangChain is available, defers to an injected LLM chain for scoring.
"""

from __future__ import annotations

import os
from typing import Callable, Iterable, List


class AuditFinding:
    def __init__(self, message: str, severity: str = "info"):
        self.message = message
        self.severity = severity

    def __repr__(self) -> str:  # pragma: no cover - human-readable helper
        return f"AuditFinding(severity={self.severity}, message={self.message})"


def run_heuristic_audit(
    items: Iterable[str],
    llm_chain_factory: Callable[[], object] | None = None,
    enabled_env: str = "HEURISTIC_AUDIT",
) -> List[AuditFinding]:
    """Run heuristic audit; if LangChain is present and enabled, use it to score items."""
    if os.environ.get(enabled_env, "0") != "1":
        return []

    findings: list[AuditFinding] = []
    # Basic heuristics: flag empty entries and long entries as potential issues.
    for idx, item in enumerate(items):
        if not item or not item.strip():
            findings.append(AuditFinding(f"Item {idx} is empty", "warning"))
        if len(item) > 500:
            findings.append(AuditFinding(f"Item {idx} is very long", "info"))

    # Optional LangChain path
    if llm_chain_factory:
        try:
            chain = llm_chain_factory()
            # Expect chain to provide a simple invoke method
            for idx, item in enumerate(items):
                result = chain.invoke(item)  # type: ignore[call-arg]
                if isinstance(result, str) and result.strip():
                    findings.append(AuditFinding(f"LLM note for item {idx}: {result}", "info"))
        except Exception:
            # If LangChain path fails, stay silent to avoid test fragility.
            pass

    return findings


def default_langchain_chain():
    """Provide a minimal LangChain LLM chain if installed; otherwise raise ImportError."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain.chat_models import init_chat_model

    prompt = ChatPromptTemplate.from_template(
        "Review the test log chunk and emit one concise risk observation if any:\n\n{log_chunk}"
    )
    model = init_chat_model("gpt-4o-mini", temperature=0)
    return prompt | model | RunnablePassthrough()
