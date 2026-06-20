"""Ruri v3 embedding wrapper — requires [vector] extras.

Uses sentence-transformers for correct mean pooling (Ruri v3 公式推奨)."""

from __future__ import annotations

import numpy as np

_MODEL_NAME = "cl-nagoya/ruri-v3-310m"
_QUERY_PREFIX = "検索クエリ: "
_DOC_PREFIX = "検索文書: "


class RuriEmbedder:
    def __init__(self, model_name: str = _MODEL_NAME, device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)
        self._device = device

    def embed_query(self, text: str) -> np.ndarray:
        return self._model.encode(_QUERY_PREFIX + text, normalize_embeddings=True)

    def embed_document(self, text: str) -> np.ndarray:
        return self._model.encode(_DOC_PREFIX + text, normalize_embeddings=True)

    def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> np.ndarray:
        prefixed = [_DOC_PREFIX + t for t in texts]
        return self._model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

    @property
    def dim(self) -> int:
        return self._model.get_sentence_embedding_dimension()
