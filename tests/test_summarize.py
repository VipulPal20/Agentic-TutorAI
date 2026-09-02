"""Tests for the notes summariser with a mocked Gemini model."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from agent import summarize as summarize_mod
from agent.summarize import _render_transcript, summarize_conversation
from core.exceptions import AgentError


class FakeModel:
    def __init__(self, content="# Notes\nAll good.") -> None:
        self._content = content
        self.seen: list = []

    async def ainvoke(self, messages):
        self.seen = messages
        return AIMessage(content=self._content)


class BoomModel:
    async def ainvoke(self, messages):
        raise RuntimeError("quota exceeded")


def test_render_transcript_labels_roles() -> None:
    rendered = _render_transcript([("user", "What is RAG?"), ("assistant", "It is...")])
    assert "Question: What is RAG?" in rendered
    assert "Answer: It is..." in rendered


async def test_summarize_returns_markdown(monkeypatch) -> None:
    model = FakeModel()
    monkeypatch.setattr(summarize_mod, "get_chat_model", lambda: model)

    notes = await summarize_conversation([("user", "q"), ("assistant", "a")])

    assert notes == "# Notes\nAll good."
    # The transcript must actually reach the model.
    assert "Question: q" in model.seen[-1].content


async def test_summarize_joins_content_parts(monkeypatch) -> None:
    model = FakeModel(content=[{"type": "text", "text": "# Notes\n"}, {"text": "body"}])
    monkeypatch.setattr(summarize_mod, "get_chat_model", lambda: model)

    notes = await summarize_conversation([("user", "q")])
    assert notes == "# Notes\nbody"


async def test_summarize_rejects_empty_conversation() -> None:
    with pytest.raises(AgentError):
        await summarize_conversation([])


async def test_summarize_wraps_model_errors(monkeypatch) -> None:
    monkeypatch.setattr(summarize_mod, "get_chat_model", lambda: BoomModel())

    with pytest.raises(AgentError) as excinfo:
        await summarize_conversation([("user", "q")])

    assert "Could not generate notes" in str(excinfo.value)
