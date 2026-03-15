"""Embedding providers for semantic memory retrieval.

Provider format:
    "openai:text-embedding-3-small"
    "fastembed:bge-small-en-v1.5"
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional
from config import logger, configuration


class OpenAIEmbedding():
    def __init__(self, model: str = "text-embedding-3-small", base_url: Optional[str] = None) -> None:
        self.model = model
        self.base_url = base_url
        self._client: Any = None

    def init(self) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError("Install optional dependency 'openai' for embeddings") from e

        self._client = AsyncOpenAI(base_url=self.base_url)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return list(response.data[0].embedding)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]


class FastEmbedEmbedding():
    _ALIASES = {
        "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
        "nomic-embed-base": "nomic-ai/nomic-embed-text-v1.5",
        "nomic-embed-text-v1.5": "nomic-ai/nomic-embed-text-v1.5",
    }

    def __init__(self, model: str = "bge-small-en-v1.5") -> None:
        self.model = model
        self._model: Any = None

    def init(self) -> None:
        try:
            from fastembed import TextEmbedding  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError("Install optional dependency 'fastembed' for local embeddings") from e

        model_name = self._ALIASES.get(self.model, self.model)
        self._model = TextEmbedding(model_name=model_name)

    async def embed(self, text: str) -> list[float]:
        def _run() -> list[float]:
            output = next(iter(self._model.embed([text])))
            return output.tolist() if hasattr(output, "tolist") else [float(v) for v in output]

        return await asyncio.to_thread(_run)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        def _run() -> list[list[float]]:
            return [
                o.tolist() if hasattr(o, "tolist") else [float(v) for v in o]
                for o in self._model.embed(texts)
            ]
        return await asyncio.to_thread(_run)


class EmbeddingEngine:
    """Provider-agnostic embedding facade with safe degradation."""

    def __init__(self) -> None:
        self._enabled = False
        self._dimension: Optional[int] = None
        self._embedding: Optional[OpenAIEmbedding | FastEmbedEmbedding] = None

        self.service = configuration.get("embedding", {}) or {}
        self.base_url: Optional[str] = None
        self.model: Optional[str] = None
        self.provider: Optional[str] = None

        if not self.service:
            logger.info("No embedding provider configured; embeddings disabled")
            return

        if not isinstance(self.service, dict):
            logger.warning(
                "Invalid embedding config type; expected dict, got %s",
                type(self.service).__name__,
            )
            return

        self.base_url = self.service.get("base_url")
        self.model = self.service.get("model")
        self.provider = self.service.get("provider")

    def provider_id(self) -> Optional[str]:
        return self.provider

    def model_id(self) -> Optional[str]:
        return self.model

    def init_model(self) -> None:
        self._enabled = False
        self._embedding = None

        if not self.provider or not self.model:
            logger.warning(
                "EmbeddingEngine: missing provider/model in config (provider=%s, model=%s)",
                self.provider,
                self.model,
            )
            return

        try:
            if self.provider == "openai":
                self._embedding = OpenAIEmbedding(self.model, base_url=self.base_url)
            elif self.provider == "fastembed":
                self._embedding = FastEmbedEmbedding(self.model)
            else:
                raise ValueError(f"Unsupported embedding provider: {self.provider}")

            self._embedding.init()
            self._enabled = True
            logger.debug("EmbeddingEngine: initialized %s:%s", self.provider, self.model)
        except Exception as e:
            self._enabled = False
            logger.warning("EmbeddingEngine init failed for %s:%s - %s", self.provider, self.model, e)

    async def embed_one(self, text: str) -> Optional[list[float]]:
        """Return embedding vector for text, or None when disabled/failing."""
        if not self._enabled or not self._embedding:
            return None

        if not text or not text.strip():
            logger.warning("EmbeddingEngine: empty text, skipping embedding")
            return None

        try:
            vector = await self._embedding.embed(text)
            if self._dimension is None:
                self._dimension = len(vector)
            return vector
        except Exception as e:
            logger.warning(f"EmbeddingEngine: {self.provider} embedding failed - {e}")
            return None

    async def embed_many(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Embed multiple texts. Returns list parallel to input; None for empty/failed."""
        if not self._enabled or not self._embedding:
            return [None] * len(texts)

        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid_indices:
            return [None] * len(texts)

        payload = [texts[i].strip() for i in valid_indices]
        result: list[Optional[list[float]]] = [None] * len(texts)

        try:
            vectors = await self._embedding.embed_many(payload)

            if len(vectors) != len(payload):
                logger.warning(
                    "EmbeddingEngine: batch size mismatch (input=%s output=%s)",
                    len(payload),
                    len(vectors),
                )

            for pos, idx in enumerate(valid_indices):
                if pos >= len(vectors):
                    break
                vec = vectors[pos]
                result[idx] = vec
                if self._dimension is None and vec:
                    self._dimension = len(vec)

            return result
        except Exception as e:
            logger.warning("EmbeddingEngine: batch embed failed - %s", e)
            return [None] * len(texts)
