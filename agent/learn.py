"""Core learning generator using RAG document retrieval + Groq LLM JSON output."""

from __future__ import annotations

import json
import random
import uuid
from typing import Any

from api.schemas import (
    Explanation,
    ExplanationSection,
    Flashcard,
    KnowledgeGap,
    LearnRequest,
    LearnResponse,
    QuizQuestion,
    SourceReference,
    StudentMastery,
)
from core.exceptions import AppError
from core.llm import get_chat_model, get_embeddings
from core.logging import get_logger
from database.repository import fetch_sample_chunks, similarity_search

logger = get_logger(__name__)


async def generate_learn_content(req: LearnRequest) -> LearnResponse:
    """Generate grounded learning content (quiz, flashcard, explain, or assessment)."""
    # 1. Retrieve grounded context from knowledge base
    chunks: list[dict[str, Any]] = []

    if req.topic and req.topic.strip():
        topic_clean = req.topic.strip()
        try:
            embedder = get_embeddings()
            query_vec = await embedder.aembed_query(topic_clean)
            chunks = await similarity_search(query_vec, top_k=6)
        except Exception as exc:
            logger.warning("Vector search for topic '%s' failed, falling back to sample search: %s", topic_clean, exc)
            chunks = await fetch_sample_chunks(limit=6, topic=topic_clean)
    else:
        chunks = await fetch_sample_chunks(limit=8)

    if not chunks:
        # Fall back to any sample chunks in the database
        chunks = await fetch_sample_chunks(limit=6)

    if not chunks:
        raise AppError(
            "No document sources found in knowledge base. Please upload documents first.",
            status_code=400,
        )

    # Format context passages for LLM
    context_blocks = []
    sources_used = set()
    for idx, c in enumerate(chunks, 1):
        src = c.get("metadata", {}).get("source", "Unknown Document")
        pg = c.get("metadata", {}).get("page")
        pg_str = f" (page {pg})" if pg else ""
        sources_used.add(src)
        context_blocks.append(
            f"[Passage {idx} | Source: {src}{pg_str}]\n{c['content']}"
        )

    combined_context = "\n\n---\n\n".join(context_blocks)
    topic_display = req.topic.strip() if (req.topic and req.topic.strip()) else "Knowledge Base Synthesis"

    # 2. Call Groq to generate structured content
    llm = get_chat_model()

    if req.mode == "quiz" or req.mode == "assessment":
        return await _generate_quiz(
            llm=llm,
            context=combined_context,
            topic=topic_display,
            difficulty=req.difficulty,
            count=req.count,
            mode=req.mode,
            sources_used=list(sources_used),
            raw_chunks=chunks,
        )
    elif req.mode == "flashcard":
        return await _generate_flashcards(
            llm=llm,
            context=combined_context,
            topic=topic_display,
            count=req.count,
            sources_used=list(sources_used),
            raw_chunks=chunks,
        )
    elif req.mode == "explain":
        return await _generate_explanation(
            llm=llm,
            context=combined_context,
            topic=topic_display,
            sources_used=list(sources_used),
            raw_chunks=chunks,
        )
    else:
        return await _generate_quiz(
            llm=llm,
            context=combined_context,
            topic=topic_display,
            difficulty=req.difficulty,
            count=req.count,
            mode="quiz",
            sources_used=list(sources_used),
            raw_chunks=chunks,
        )


async def _generate_quiz(
    llm: Any,
    context: str,
    topic: str,
    difficulty: str,
    count: int,
    mode: str,
    sources_used: list[str],
    raw_chunks: list[dict],
) -> LearnResponse:
    prompt = f"""You are an expert AI tutor. Generate a high-quality {count}-question multiple choice quiz testing comprehension of the provided knowledge base context.

Topic: {topic}
Target Difficulty: {difficulty}

CONTEXT FROM KNOWLEDGE BASE:
{context}

REQUIREMENTS:
1. Every question MUST be grounded in the context provided.
2. Return ONLY a valid JSON object matching this schema (no markdown wrap or extra commentary):
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": 0,  // 0-based integer index of correct option
      "explanation": "Detailed explanation of why this option is correct based on the context.",
      "concept": "Specific concept name",
      "source_document": "Name of source file if available in context",
      "source_page": 1  // Integer page number if mentioned or null
    }}
  ]
}}

Generate exactly {count} distinct questions. Return pure JSON.
"""

    response = await llm.ainvoke(prompt)
    content = str(response.content).strip()

    # Clean JSON if wrapped in markdown code blocks
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse quiz JSON from LLM: %s. Raw output: %s", exc, content[:500])
        raise AppError("Failed to generate structured quiz content. Please try again.", status_code=500) from exc

    raw_questions = data.get("questions", [])
    questions: list[QuizQuestion] = []
    concepts_found: list[str] = []

    default_src = sources_used[0] if sources_used else "Knowledge Base"

    for q in raw_questions:
        doc = q.get("source_document") or default_src
        pg = q.get("source_page")
        concept = q.get("concept") or topic

        if concept and concept not in concepts_found:
            concepts_found.append(concept)

        questions.append(
            QuizQuestion(
                id=str(uuid.uuid4())[:8],
                question=q.get("question", "Question"),
                options=q.get("options", ["A", "B", "C", "D"]),
                correct_answer=int(q.get("correct_answer", 0)),
                explanation=q.get("explanation", "Grounded in context."),
                concept=concept,
                difficulty=difficulty,
                source=SourceReference(document=str(doc), page=pg if isinstance(pg, int) else None),
            )
        )

    mastery = StudentMastery(
        topic=topic,
        mastery_pct=65 if difficulty == "easy" else (50 if difficulty == "medium" else 40),
        strong_concepts=concepts_found[:2],
        weak_concepts=concepts_found[2:] if len(concepts_found) > 2 else [f"{topic} Advanced Application"],
        gaps=[
            KnowledgeGap(
                concept=c,
                explanation=f"Review passages related to {c} in {default_src}.",
                severity="medium",
            )
            for c in (concepts_found[2:] if len(concepts_found) > 2 else [f"{topic} core principles"])
        ],
    )

    return LearnResponse(
        mode=mode,
        topic=topic,
        questions=questions,
        mastery=mastery,
        sources_used=sources_used,
    )


async def _generate_flashcards(
    llm: Any,
    context: str,
    topic: str,
    count: int,
    sources_used: list[str],
    raw_chunks: list[dict],
) -> LearnResponse:
    prompt = f"""You are an expert AI tutor. Generate {count} flashcards for quick revision based on the provided knowledge base context.

Topic: {topic}

CONTEXT FROM KNOWLEDGE BASE:
{context}

REQUIREMENTS:
1. Return ONLY a valid JSON object matching this schema:
{{
  "flashcards": [
    {{
      "concept": "Concept Title",
      "front": "Question / Prompt on card front",
      "back": "Clear concise answer and summary on card back",
      "source_document": "Source file name"
    }}
  ]
}}

Generate exactly {count} flashcards. Return pure JSON.
"""

    response = await llm.ainvoke(prompt)
    content = str(response.content).strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse flashcards JSON: %s", exc)
        raise AppError("Failed to generate flashcard content.", status_code=500) from exc

    default_src = sources_used[0] if sources_used else "Knowledge Base"
    flashcards: list[Flashcard] = []

    for fc in data.get("flashcards", []):
        doc = fc.get("source_document") or default_src
        flashcards.append(
            Flashcard(
                id=str(uuid.uuid4())[:8],
                concept=fc.get("concept", topic),
                front=fc.get("front", "Concept Prompt"),
                back=fc.get("back", "Concept Explanation"),
                source=SourceReference(document=str(doc)),
            )
        )

    return LearnResponse(
        mode="flashcard",
        topic=topic,
        flashcards=flashcards,
        sources_used=sources_used,
    )


async def _generate_explanation(
    llm: Any,
    context: str,
    topic: str,
    sources_used: list[str],
    raw_chunks: list[dict],
) -> LearnResponse:
    prompt = f"""You are an expert AI tutor. Write a structured, comprehensive lesson explaining '{topic}' based on the context provided.

CONTEXT FROM KNOWLEDGE BASE:
{context}

REQUIREMENTS:
Return ONLY a valid JSON object with this exact schema:
{{
  "topic": "{topic}",
  "overview": "Clear 2-3 sentence overview of the topic.",
  "sections": [
    {{
      "title": "Section Title (e.g., 1. What is it?)",
      "content": "Detailed explanation using markdown..."
    }}
  ],
  "key_takeaways": [
    "Takeaway point 1",
    "Takeaway point 2"
  ],
  "misconceptions": [
    "Common misunderstanding 1 and why it is wrong"
  ]
}}

Return pure JSON.
"""

    response = await llm.ainvoke(prompt)
    content = str(response.content).strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse explanation JSON: %s", exc)
        raise AppError("Failed to generate lesson explanation.", status_code=500) from exc

    default_src = sources_used[0] if sources_used else "Knowledge Base"
    sections = [
        ExplanationSection(title=s.get("title", "Overview"), content=s.get("content", ""))
        for s in data.get("sections", [])
    ]

    explanation = Explanation(
        topic=data.get("topic", topic),
        overview=data.get("overview", "Lesson overview based on retrieved knowledge."),
        sections=sections,
        key_takeaways=data.get("key_takeaways", []),
        misconceptions=data.get("misconceptions", []),
        source=SourceReference(document=default_src),
    )

    return LearnResponse(
        mode="explain",
        topic=topic,
        explanation=explanation,
        sources_used=sources_used,
    )
