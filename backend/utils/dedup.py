"""Deduplication utility for news items using semantic similarity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import numpy as np
from config import logger
from backend.core.database import DataInterface
from backend.core.redis import tracker
from backend.models.data import RawNewsItem

SIMILARITY_THRESHOLD = 0.82


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def check_duplicate(
    database: DataInterface,
    raw_data: RawNewsItem,
    embedding: List[float],
    hours: int = 72,
) -> Optional[RawNewsItem]:
    """Check if a news item is a duplicate of a recently classified item.

    Compares the embedding against items from the last `hours` hours that share
    at least one entity.  Returns the best match above SIMILARITY_THRESHOLD,
    or None.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    candidates: list[RawNewsItem] = await database.load_raw_news(
        time_range=(start, now), limit=500
    )

    if not candidates:
        return None

    current_entities = set(e.lower() for e in raw_data.entities) if raw_data.entities else set()

    best_match: Optional[RawNewsItem] = None
    best_score: float = 0.0

    for candidate in candidates:
        # Skip self
        if candidate.id == raw_data.id:
            continue

        # Must have an embedding stored
        if not candidate.embedding:
            continue

        # Entity overlap filter — at least 1 shared entity
        if current_entities:
            candidate_entities = set(e.lower() for e in candidate.entities) if candidate.entities else set()
            if not current_entities & candidate_entities:
                continue

        score = cosine_similarity(embedding, candidate.embedding)

        if score > best_score:
            best_score = score
            best_match = candidate

    # Log the best similarity for tuning
    if best_match:
        await tracker.log(
            str(raw_data.id),
            f"Dedup: best similarity {best_score:.4f} with #{best_match.id} "
            f"(threshold {SIMILARITY_THRESHOLD})",
        )

    if best_score >= SIMILARITY_THRESHOLD and best_match is not None:
        return best_match

    return None
