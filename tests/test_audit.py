import os

from conestoga.game.audit import AuditFinding, run_heuristic_audit


class DummyChain:
    def __init__(self):
        self.seen = []

    def invoke(self, item):
        self.seen.append(item)
        return f"checked:{len(item)}"


def test_heuristic_audit_runs_when_enabled(monkeypatch):
    monkeypatch.setenv("HEURISTIC_AUDIT", "1")
    findings = run_heuristic_audit(["", "ok", "x" * 501])
    messages = [f.message for f in findings]
    assert any("empty" in m for m in messages)
    assert any("very long" in m for m in messages)


def test_heuristic_audit_with_langchain_stub(monkeypatch):
    monkeypatch.setenv("HEURISTIC_AUDIT", "1")
    chain = DummyChain()
    findings = run_heuristic_audit(["abc"], llm_chain_factory=lambda: chain)
    assert any(isinstance(f, AuditFinding) and "LLM note" in f.message for f in findings)
    assert chain.seen == ["abc"]


def test_heuristic_audit_disabled(monkeypatch):
    monkeypatch.delenv("HEURISTIC_AUDIT", raising=False)
    findings = run_heuristic_audit(["abc"])
    assert findings == []
