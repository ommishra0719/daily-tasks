"""Strategy pattern implementation for document chunking."""

import re
from abc import ABC, abstractmethod
from typing import Any


class ChunkerStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str) -> list[str]:
        """
        Chunk text according to strategy.

        Args:
            text: Text to chunk

        Returns:
            List of chunks
        """
        pass

    def validate_input(self, text: str | None) -> str:
        """
        Validate and prepare input text.

        Args:
            text: Input text

        Returns:
            Validated and cleaned text

        Raises:
            ValueError: If text is invalid
        """
        if text is None:
            raise ValueError("Text cannot be None")

        if not isinstance(text, str):
            raise ValueError("Text must be a string")

        return text.strip()


class FixedSizeChunker(ChunkerStrategy):
    """Chunk text by fixed character count."""

    def __init__(self, chunk_size: int = 100):
        """
        Initialize fixed-size chunker.

        Args:
            chunk_size: Characters per chunk
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        """
        Split text into fixed-size chunks.

        Args:
            text: Text to chunk

        Returns:
            List of chunks

        Example:
            >>> chunker = FixedSizeChunker(chunk_size=20)
            >>> chunks = chunker.chunk("Hello world this is a test")
            >>> len(chunks)
            2
        """
        text = self.validate_input(text)

        if not text:
            return []

        return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]


class SentenceChunker(ChunkerStrategy):
    """Chunk text by sentences."""

    # Regex pattern for sentence boundaries
    SENTENCE_PATTERN = re.compile(r"[.!?]+")

    def chunk(self, text: str) -> list[str]:
        """
        Split text into sentences.

        Args:
            text: Text to chunk

        Returns:
            List of sentences

        Example:
            >>> chunker = SentenceChunker()
            >>> chunks = chunker.chunk("Hello world. This is great! How are you?")
            >>> len(chunks)
            3
        """
        text = self.validate_input(text)

        if not text:
            return []

        # Split on sentence boundaries, keeping trailing punctuation
        sentences = self.SENTENCE_PATTERN.split(text)
        # Filter out empty strings and strip whitespace
        return [s.strip() for s in sentences if s.strip()]


class RecursiveChunker(ChunkerStrategy):
    """Hierarchically chunk text: paragraphs → sentences → words."""

    def __init__(self, max_chunk_size: int = 200):
        """
        Initialize recursive chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
        """
        self.max_chunk_size = max_chunk_size
        self.sentence_chunker = SentenceChunker()

    def chunk(self, text: str) -> list[str]:
        """
        Recursively chunk text at multiple levels.

        Args:
            text: Text to chunk

        Returns:
            List of chunks

        Example:
            >>> chunker = RecursiveChunker(max_chunk_size=50)
            >>> chunks = chunker.chunk("Paragraph one. Second sentence here.\\n\\nParagraph two.")
        """
        text = self.validate_input(text)

        if not text:
            return []

        chunks: list[str] = []
        current_chunk = ""

        # Split by paragraphs (double newlines)
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            if not para.strip():
                continue

            # Split paragraph into sentences
            sentences = self.sentence_chunker.chunk(para)

            for sentence in sentences:
                # Add sentence to current chunk if it fits
                test_chunk = (current_chunk + " " + sentence).strip()

                if len(test_chunk) <= self.max_chunk_size:
                    current_chunk = test_chunk
                else:
                    # Current chunk is full, save and start new one
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks


class DocumentProcessor:
    """Context class for strategy pattern: can swap chunking strategies at runtime."""

    def __init__(self, strategy: ChunkerStrategy):
        """
        Initialize document processor with a chunking strategy.

        Args:
            strategy: ChunkerStrategy implementation
        """
        self._strategy = strategy

    def set_strategy(self, strategy: ChunkerStrategy) -> None:
        """
        Change chunking strategy at runtime.

        Args:
            strategy: New ChunkerStrategy implementation
        """
        self._strategy = strategy

    def process(self, text: str) -> list[str]:
        """
        Process text using current strategy.

        Args:
            text: Text to process

        Returns:
            List of chunks

        Example:
            >>> processor = DocumentProcessor(FixedSizeChunker(50))
            >>> chunks = processor.process("This is a test")
            >>> processor.set_strategy(SentenceChunker())
            >>> chunks = processor.process("This is a test. Another sentence.")
        """
        return self._strategy.chunk(text)

    def get_strategy_info(self) -> dict[str, Any]:
        """
        Get information about current strategy.

        Returns:
            Dictionary with strategy details
        """
        strategy_name = self._strategy.__class__.__name__
        strategy_attrs = {}

        if isinstance(self._strategy, FixedSizeChunker):
            strategy_attrs["chunk_size"] = self._strategy.chunk_size
        elif isinstance(self._strategy, RecursiveChunker):
            strategy_attrs["max_chunk_size"] = self._strategy.max_chunk_size

        return {"strategy": strategy_name, "attributes": strategy_attrs}
