"""Tests for strategy pattern module."""

import pytest

from python_advanced.strategy import (
    DocumentProcessor,
    FixedSizeChunker,
    RecursiveChunker,
    SentenceChunker,
)


class TestFixedSizeChunker:
    """Test FixedSizeChunker strategy."""

    def test_fixed_size_chunker_basic(self) -> None:
        """Test basic fixed-size chunking."""
        chunker = FixedSizeChunker(chunk_size=5)
        chunks = chunker.chunk("Hello World")
        assert chunks == ["Hello", " Worl", "d"]

    def test_fixed_size_chunker_exact_fit(self) -> None:
        """Test chunking that fits exactly."""
        chunker = FixedSizeChunker(chunk_size=5)
        chunks = chunker.chunk("Hello")
        assert chunks == ["Hello"]

    def test_fixed_size_chunker_empty_string(self) -> None:
        """Test chunking empty string."""
        chunker = FixedSizeChunker(chunk_size=5)
        chunks = chunker.chunk("")
        assert chunks == []

    def test_fixed_size_chunker_invalid_chunk_size(self) -> None:
        """Test that invalid chunk size raises error."""
        with pytest.raises(ValueError):
            FixedSizeChunker(chunk_size=0)

    def test_fixed_size_chunker_none_input(self) -> None:
        """Test that None input raises error."""
        chunker = FixedSizeChunker(chunk_size=5)
        with pytest.raises(ValueError):
            chunker.chunk(None)  # type: ignore


class TestSentenceChunker:
    """Test SentenceChunker strategy."""

    def test_sentence_chunker_basic(self) -> None:
        """Test basic sentence chunking."""
        chunker = SentenceChunker()
        chunks = chunker.chunk("Hello world. How are you?")
        assert len(chunks) == 2
        assert "Hello world" in chunks[0]
        assert "How are you" in chunks[1]

    def test_sentence_chunker_multiple_punctuation(self) -> None:
        """Test sentence chunking with various punctuation."""
        chunker = SentenceChunker()
        text = "First sentence. Second one! Third one?"
        chunks = chunker.chunk(text)
        assert len(chunks) == 3

    def test_sentence_chunker_empty_string(self) -> None:
        """Test chunking empty string."""
        chunker = SentenceChunker()
        chunks = chunker.chunk("")
        assert chunks == []

    def test_sentence_chunker_no_punctuation(self) -> None:
        """Test chunking text without sentence boundaries."""
        chunker = SentenceChunker()
        chunks = chunker.chunk("Just a simple sentence")
        assert len(chunks) == 1
        assert chunks[0] == "Just a simple sentence"


class TestRecursiveChunker:
    """Test RecursiveChunker strategy."""

    def test_recursive_chunker_basic(self) -> None:
        """Test basic recursive chunking."""
        chunker = RecursiveChunker(max_chunk_size=50)
        text = "First paragraph. Second sentence here.\n\nSecond paragraph. Another sentence."
        chunks = chunker.chunk(text)
        assert len(chunks) > 0
        # All chunks should be within max size
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_recursive_chunker_single_paragraph(self) -> None:
        """Test recursive chunking with single paragraph."""
        chunker = RecursiveChunker(max_chunk_size=100)
        text = "This is a single paragraph. With multiple sentences. And more text here."
        chunks = chunker.chunk(text)
        assert len(chunks) > 0

    def test_recursive_chunker_empty_string(self) -> None:
        """Test recursive chunking empty string."""
        chunker = RecursiveChunker(max_chunk_size=50)
        chunks = chunker.chunk("")
        assert chunks == []


class TestDocumentProcessor:
    """Test DocumentProcessor context for strategy pattern."""

    def test_document_processor_fixed_size(self) -> None:
        """Test processor with FixedSizeChunker."""
        processor = DocumentProcessor(FixedSizeChunker(chunk_size=10))
        chunks = processor.process("Hello world test")
        assert len(chunks) > 0

    def test_document_processor_strategy_switching(self) -> None:
        """Test switching strategies at runtime."""
        processor = DocumentProcessor(FixedSizeChunker(chunk_size=10))
        chunks1 = processor.process("Hello world test string")

        processor.set_strategy(SentenceChunker())
        chunks2 = processor.process("Hello. World. Test.")

        # Results should have content (not necessarily different lengths)
        assert len(chunks1) > 0
        assert len(chunks2) > 0

    def test_document_processor_strategy_info(self) -> None:
        """Test getting strategy information."""
        processor = DocumentProcessor(FixedSizeChunker(chunk_size=15))
        info = processor.get_strategy_info()

        assert info["strategy"] == "FixedSizeChunker"
        assert info["attributes"]["chunk_size"] == 15

    def test_document_processor_recursive_info(self) -> None:
        """Test getting recursive chunker strategy info."""
        processor = DocumentProcessor(RecursiveChunker(max_chunk_size=200))
        info = processor.get_strategy_info()

        assert info["strategy"] == "RecursiveChunker"
        assert info["attributes"]["max_chunk_size"] == 200
