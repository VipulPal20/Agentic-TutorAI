"""Pydantic v2 request/response models for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat query."""

    query: str = Field(
        min_length=1,
        max_length=4000,
        description="The user's natural-language question.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional client-supplied session id (used for tracing).",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user identifier (used for tracing).",
    )


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    answer: str
    session_id: str | None = None


class HealthResponse(BaseModel):
    """Liveness/readiness payload."""

    status: str
    database: str
    document_count: int | None = None


class TranscriptTurn(BaseModel):
    """A single turn of a conversation, as sent by the client for summarising."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class SummarizeRequest(BaseModel):
    """A conversation to turn into notes."""

    turns: list[TranscriptTurn] = Field(
        min_length=1,
        max_length=100,
        description="Ordered conversation turns to summarise.",
    )


class SummarizeResponse(BaseModel):
    """Markdown notes generated from a conversation."""

    notes: str


class ErrorResponse(BaseModel):
    """Uniform error envelope returned by the exception handlers."""

    error: str
    detail: str | None = None


# ---------------------------------------------------------------------------
# Upload / knowledge-base schemas
# ---------------------------------------------------------------------------


class UploadFileResult(BaseModel):
    """Result for a single uploaded file."""

    filename: str
    chunks_stored: int
    status: Literal["ok", "error"]
    detail: str | None = None


class UploadResponse(BaseModel):
    """Response for POST /upload (one entry per file)."""

    uploaded: list[UploadFileResult]


class SourceItem(BaseModel):
    """One source file in the knowledge base."""

    source: str
    chunk_count: int
    uploaded_at: str | None = None


class SourcesResponse(BaseModel):
    """Response for GET /sources."""

    sources: list[SourceItem]
    total_chunks: int


class DeleteSourceResponse(BaseModel):
    """Response for DELETE /sources/{name}."""

    source: str
    chunks_deleted: int


# ---------------------------------------------------------------------------
# Learn Me schemas
# ---------------------------------------------------------------------------


class SourceReference(BaseModel):
    """Reference to the underlying document chunk for grounded learning."""

    document: str
    page: int | None = None
    snippet: str | None = None


class QuizQuestion(BaseModel):
    """Multiple choice quiz item."""

    id: str
    question: str
    options: list[str]
    correct_answer: int = Field(
        description="0-indexed index of the correct option in options list."
    )
    explanation: str
    source: SourceReference | None = None
    concept: str | None = None
    difficulty: str = "medium"


class Flashcard(BaseModel):
    """Flip-card concept item."""

    id: str
    concept: str
    front: str
    back: str
    source: SourceReference | None = None


class ExplanationSection(BaseModel):
    """A subsection of a structured lesson."""

    title: str
    content: str


class Explanation(BaseModel):
    """Structured AI-generated lesson."""

    topic: str
    overview: str
    sections: list[ExplanationSection] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    source: SourceReference | None = None


class KnowledgeGap(BaseModel):
    """Detected area requiring review."""

    concept: str
    explanation: str
    severity: Literal["low", "medium", "high"] = "medium"


class StudentMastery(BaseModel):
    """Overall student knowledge profile for the topic."""

    topic: str
    mastery_pct: int = Field(ge=0, le=100, default=50)
    strong_concepts: list[str] = Field(default_factory=list)
    weak_concepts: list[str] = Field(default_factory=list)
    gaps: list[KnowledgeGap] = Field(default_factory=list)


class LearnRequest(BaseModel):
    """Request payload for POST /learn."""

    topic: str | None = Field(
        default=None,
        description="Optional topic filter. If omitted, generates from overall knowledge base.",
    )
    mode: Literal["quiz", "flashcard", "explain", "assessment"] = Field(
        default="quiz",
        description="Learning mode.",
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium",
        description="Target difficulty level.",
    )
    count: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of questions or flashcards to generate.",
    )


class LearnResponse(BaseModel):
    """Response payload for POST /learn."""

    mode: str
    topic: str
    questions: list[QuizQuestion] | None = None
    flashcards: list[Flashcard] | None = None
    explanation: Explanation | None = None
    mastery: StudentMastery | None = None
    sources_used: list[str] = Field(default_factory=list)


