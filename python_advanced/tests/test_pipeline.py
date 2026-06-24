"""Tests for pipeline module."""

import tempfile
from pathlib import Path

from python_advanced.pipeline import (
    chunk_lines,
    clean_lines,
    document_pipeline,
    process_file,
    read_lines,
)


class TestReadLines:
    """Test read_lines generator."""

    def test_read_lines_from_file(self) -> None:
        """Test reading lines from a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line 1\nline 2\nline 3\n")
            f.flush()
            filepath = f.name

        try:
            lines = list(read_lines(filepath))
            assert len(lines) == 3
            assert lines[0] == "line 1\n"
            assert lines[2] == "line 3\n"
        finally:
            Path(filepath).unlink()

    def test_read_lines_empty_file(self) -> None:
        """Test reading from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.flush()
            filepath = f.name

        try:
            lines = list(read_lines(filepath))
            assert len(lines) == 0
        finally:
            Path(filepath).unlink()


class TestCleanLines:
    """Test clean_lines generator."""

    def test_clean_lines_removes_whitespace(self) -> None:
        """Test that clean_lines strips whitespace."""
        lines = ["  hello  \n", "  world  \n"]
        cleaned = list(clean_lines(iter(lines)))
        assert cleaned == ["hello", "world"]

    def test_clean_lines_filters_empty_lines(self) -> None:
        """Test that clean_lines filters empty lines."""
        lines = ["hello\n", "  \n", "world\n", "\n"]
        cleaned = list(clean_lines(iter(lines)))
        assert cleaned == ["hello", "world"]


class TestChunkLines:
    """Test chunk_lines generator."""

    def test_chunk_lines_basic(self) -> None:
        """Test basic line chunking."""
        lines = iter(["a", "b", "c", "d", "e"])
        chunks = list(chunk_lines(lines, chunk_size=2))
        assert len(chunks) == 3
        assert chunks[0] == ["a", "b"]
        assert chunks[1] == ["c", "d"]
        assert chunks[2] == ["e"]

    def test_chunk_lines_exact_division(self) -> None:
        """Test chunking with exact division."""
        lines = iter(["a", "b", "c", "d"])
        chunks = list(chunk_lines(lines, chunk_size=2))
        assert len(chunks) == 2
        assert chunks[0] == ["a", "b"]
        assert chunks[1] == ["c", "d"]

    def test_chunk_lines_empty_input(self) -> None:
        """Test chunking empty input."""
        lines = iter([])
        chunks = list(chunk_lines(lines, chunk_size=2))
        assert len(chunks) == 0


class TestDocumentPipeline:
    """Test document_pipeline function."""

    def test_document_pipeline_integration(self) -> None:
        """Test complete pipeline."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            content = "line 1\n  \nline 2\n  line 3  \nline 4\n"
            f.write(content)
            f.flush()
            filepath = f.name

        try:
            chunks = list(document_pipeline(filepath, chunk_size=2))
            assert len(chunks) == 2
            # First chunk should have 2 cleaned lines
            assert len(chunks[0]) == 2
        finally:
            Path(filepath).unlink()


class TestProcessFile:
    """Test process_file function."""

    def test_process_file_statistics(self) -> None:
        """Test that process_file returns correct statistics."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            content = "hello\nworld\ntest\n"
            f.write(content)
            f.flush()
            filepath = f.name

        try:
            chunks, lines, chars = process_file(filepath, chunk_size=2)
            assert chunks > 0
            assert lines == 3
            assert chars > 0
        finally:
            Path(filepath).unlink()
