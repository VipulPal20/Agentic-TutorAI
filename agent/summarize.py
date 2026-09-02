"""Turn a conversation into structured study notes.

Kept separate from the ReAct graph on purpose: summarising is a single, direct
LLM call with no tools and no loop, so it doesn't belong in the agent graph.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from core.exceptions import AgentError
from core.llm import get_chat_model
from core.logging import get_logger

logger = get_logger(__name__)

NOTES_SYSTEM_PROMPT = """\
You turn a question-and-answer conversation into clean, revision-ready notes.

Produce Markdown with this shape:

# Notes
A one-paragraph summary of what the conversation covered.

## Key points
Short, factual bullets capturing the substance. Merge duplicates across turns.

## Terms
Any technical term that appeared, each with a one-line definition. Omit this
section entirely if no technical terms came up.

## Open questions
Anything left unresolved or explicitly deferred. Omit if there are none.

Rules: use only information present in the conversation — never invent facts.
Keep bullets tight and scannable. Do not add a preamble or closing remark, and
do not wrap the output in a code fence.
"""


def _render_transcript(turns: list[tuple[str, str]]) -> str:
    """Render ``(role, content)`` pairs into a plain-text transcript."""
    lines: list[str] = []
    for role, content in turns:
        speaker = "Question" if role == "user" else "Answer"
        lines.append(f"{speaker}: {content.strip()}")
    return "\n\n".join(lines)


async def summarize_conversation(turns: list[tuple[str, str]]) -> str:
    """Return Markdown notes for a conversation.

    ``turns`` is an ordered list of ``(role, content)`` pairs where role is
    ``"user"`` or ``"assistant"``. Raises :class:`AgentError` if the model call
    fails, so the central FastAPI handler can map it to a status code.
    """
    if not turns:
        raise AgentError("Cannot summarize an empty conversation.")

    transcript = _render_transcript(turns)
    model = get_chat_model()
    try:
        response = await model.ainvoke(
            [
                SystemMessage(content=NOTES_SYSTEM_PROMPT),
                HumanMessage(content=f"Conversation to turn into notes:\n\n{transcript}"),
            ]
        )
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
        logger.exception("Note summarisation failed.")
        raise AgentError(f"Could not generate notes: {exc}") from exc

    content = response.content
    if isinstance(content, list):
        parts = [
            item if isinstance(item, str) else str(item.get("text", ""))
            for item in content
        ]
        return "".join(parts).strip()
    return str(content).strip()
