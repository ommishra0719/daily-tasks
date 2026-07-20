from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-embedding-001"
CACHE_FILE = Path("embedding_cache.json")


class SemanticSearch:
    """Simple in-memory semantic search using Gemini embeddings."""

    def __init__(self) -> None:
        self.client = genai.Client()
        self.documents: List[str] = []
        self.embeddings: np.ndarray | None = None
        self.cache = self._load_cache()

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f)

    def _embed_batch(
        self,
        texts: List[str],
        task_type: str,
    ) -> List[np.ndarray]:
        """Embed a batch of texts using Gemini."""

        uncached = [text for text in texts if text not in self.cache]

        if uncached:
            response = self.client.models.embed_content(
                model=MODEL_NAME,
                contents=uncached,
                config=types.EmbedContentConfig(
                    task_type=task_type
                ),
            )

            for text, emb in zip(response.embeddings, uncached):
                vector = self._normalize(
                    np.array(text.values, dtype=np.float32)
                )
                self.cache[emb] = vector.tolist()

            self._save_cache()

        vectors = [
            np.array(self.cache[text], dtype=np.float32)
            for text in texts
        ]

        return vectors

    def index(self, documents: List[str]) -> None:
        """Embed and store documents."""

        self.documents = documents

        vectors = self._embed_batch(
            documents,
            "RETRIEVAL_DOCUMENT",
        )

        self.embeddings = np.vstack(vectors)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[tuple]:
        """Return top-k similar documents."""

        if self.embeddings is None:
            raise RuntimeError("No documents indexed.")

        query_vector = self._embed_batch(
            [query],
            "RETRIEVAL_QUERY",
        )[0]

        similarities = self.embeddings @ query_vector

        indices = np.argsort(similarities)[::-1][:top_k]

        return [
            (
                self.documents[i],
                float(similarities[i]),
            )
            for i in indices
        ]


if __name__ == "__main__":

    corpus = [
        "Python is a popular programming language.",
        "Machine learning is a branch of artificial intelligence.",
        "Neural networks are inspired by the human brain.",
        "Paris is the capital of France.",
        "The stock market fluctuates daily.",
        "Football is played worldwide.",
        "Deep learning uses many neural network layers.",
        "Cats are common household pets.",
        "Dogs are loyal companions.",
        "Quantum computing uses qubits.",
        "Cloud computing enables scalable infrastructure.",
        "The Amazon rainforest has rich biodiversity.",
        "Solar energy is renewable.",
        "Cybersecurity protects computer systems.",
        "Databases store structured information.",
        "APIs enable software communication.",
        "Electric vehicles reduce emissions.",
        "Blockchain powers cryptocurrencies.",
        "Natural language processing understands text.",
        "Large language models generate human-like responses.",
        "Docker packages applications into containers.",
        "Kubernetes orchestrates containerized applications.",
        "Git tracks source code changes.",
        "Linux is widely used on servers.",
        "Birds can migrate thousands of kilometers.",
        "Mount Everest is the tallest mountain.",
        "Water boils at 100 degrees Celsius.",
        "Photosynthesis converts sunlight into energy.",
        "Vaccines help prevent infectious diseases.",
        "Space telescopes observe distant galaxies.",
        "Computer vision analyzes images.",
        "Recommendation systems personalize content.",
        "Reinforcement learning learns through rewards.",
        "Data science combines statistics and programming.",
        "Graphs model relationships between entities.",
        "Robotics integrates hardware and AI.",
        "Smartphones contain powerful processors.",
        "Music can influence emotions.",
        "Chess requires strategic thinking.",
        "Baking bread involves yeast fermentation.",
        "Coffee contains caffeine.",
        "Ocean currents affect climate.",
        "Satellites provide GPS navigation.",
        "Memory management improves software performance.",
        "Compilers translate source code into machine code.",
        "Operating systems manage hardware resources.",
        "Distributed systems improve scalability.",
        "Encryption secures communication.",
        "Search engines index web pages.",
        "Artificial intelligence is transforming healthcare.",
    ]

    engine = SemanticSearch()
    engine.index(corpus)

    test_queries = [
        "AI for medicine",
        "How do neural networks learn?",
        "Programming language",
        "Renewable power",
        "Container orchestration",
        "Protecting networks",
        "Space exploration",
        "Pet animals",
        "Climate change",
        "Software version control",
    ]

    for query in test_queries:
        print("=" * 70)
        print(f"Query: {query}\n")

        for document, score in engine.search(query):
            print(f"{score:.4f}  {document}")