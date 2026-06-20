"""Ruri v3 embedding wrapper — requires [vector] extras."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import torch

_MODEL_NAME = "cl-nagoya/ruri-v3-310m"
_QUERY_PREFIX = "検索クエリ: "
_DOC_PREFIX = "検索文書: "


class RuriEmbedder:
    def __init__(self, model_name: str = _MODEL_NAME, device: str = "cpu") -> None:
        from transformers import AutoModel, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModel.from_pretrained(model_name).to(device)
        self._model.eval()
        self._device = device

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed(_QUERY_PREFIX + text)

    def embed_document(self, text: str) -> np.ndarray:
        return self._embed(_DOC_PREFIX + text)

    def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> np.ndarray:
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = [_DOC_PREFIX + t for t in texts[i:i + batch_size]]
            embs = self._embed_batch(batch)
            all_embs.append(embs)
        return np.vstack(all_embs)

    def _embed(self, text: str) -> np.ndarray:
        return self._embed_batch([text])[0]

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        import torch

        inputs = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=8192,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            embs = outputs.last_hidden_state[:, 0, :]
            embs = torch.nn.functional.normalize(embs, p=2, dim=1)

        return embs.cpu().numpy()

    @property
    def dim(self) -> int:
        return self._model.config.hidden_size
