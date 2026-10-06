from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class LocalSentenceTransformerProvider:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("RAG için 'pip install -e .[rag]' komutunu çalıştırın") from exc
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [vector.tolist() for vector in vectors]


def build_embedding_provider(model_name: str) -> EmbeddingProvider:
    return LocalSentenceTransformerProvider(model_name)
