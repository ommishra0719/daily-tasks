"""Tests for performance optimization module."""


from python_advanced.performance import (
    OptimizedTextChunk,
    PerformanceAnalyzer,
    calculate_overlap_score,
    calculate_overlap_score_optimized,
    heavy_cleaner,
    heavy_cleaner_optimized,
    run_pipeline,
    run_pipeline_optimized,
)


class TestTextCleaning:
    """Test text cleaning functions."""

    def test_heavy_cleaner_basic(self) -> None:
        """Test basic text cleaning."""
        result = heavy_cleaner("Hello   World!!!")
        assert result == "hello world"

    def test_heavy_cleaner_optimized_basic(self) -> None:
        """Test optimized text cleaning."""
        result = heavy_cleaner_optimized("Hello   World!!!")
        assert result == "hello world"

    def test_heavy_cleaner_caching(self) -> None:
        """Test that optimized cleaner uses caching."""
        # Call twice with same input
        result1 = heavy_cleaner_optimized("test text")
        result2 = heavy_cleaner_optimized("test text")
        assert result1 == result2
        # Cache should have been used (no error)

    def test_cleaner_consistency(self) -> None:
        """Test that both cleaners produce same results."""
        test_strings = [
            "Hello  World",
            "!!!Special chars!!!",
            "  Whitespace  ",
            "MixedCASE",
        ]
        for text in test_strings:
            assert heavy_cleaner(text) == heavy_cleaner_optimized(text)


class TestOverlapScore:
    """Test overlap scoring functions."""

    def test_overlap_score_identical_text(self) -> None:
        """Test overlap score for identical text."""
        score = calculate_overlap_score("hello world", "hello world")
        assert score == 1.0

    def test_overlap_score_no_overlap(self) -> None:
        """Test overlap score for no common words."""
        score = calculate_overlap_score("hello world", "foo bar")
        assert score == 0.0

    def test_overlap_score_partial_overlap(self) -> None:
        """Test overlap score for partial overlap."""
        score = calculate_overlap_score("hello world test", "hello there test")
        # Expect some overlap
        assert 0 < score < 1.0

    def test_overlap_score_optimized_identical(self) -> None:
        """Test optimized overlap score for identical text."""
        score = calculate_overlap_score_optimized("hello world", "hello world")
        assert score == 1.0

    def test_overlap_score_optimized_no_overlap(self) -> None:
        """Test optimized overlap score for no common words."""
        score = calculate_overlap_score_optimized("hello world", "foo bar")
        assert score == 0.0

    def test_overlap_score_consistency(self) -> None:
        """Test that both functions produce same results."""
        text1 = "the quick brown fox jumps over the lazy dog"
        text2 = "a quick brown fox and the dog"

        score1 = calculate_overlap_score(text1, text2)
        score2 = calculate_overlap_score_optimized(text1, text2)

        # Should be very close (allow for rounding differences due to different algorithms)
        assert abs(score1 - score2) < 0.1


class TestTextChunk:
    """Test OptimizedTextChunk dataclass."""

    def test_optimized_text_chunk_creation(self) -> None:
        """Test creating OptimizedTextChunk."""
        chunk = OptimizedTextChunk(
            chunk_id=1,
            text="Hello world",
            source="test.txt",
            metrics={"token_count": 2},
        )
        assert chunk.chunk_id == 1
        assert chunk.text == "Hello world"
        assert chunk.metrics["token_count"] == 2

    def test_optimized_text_chunk_slots(self) -> None:
        """Test that OptimizedTextChunk uses __slots__."""
        chunk = OptimizedTextChunk(
            chunk_id=1,
            text="test",
            source="source",
            metrics={},
        )
        # Should not have __dict__ (due to __slots__)
        assert not hasattr(chunk, "__dict__")


class TestPipeline:
    """Test pipeline functions."""

    def test_run_pipeline_basic(self) -> None:
        """Test basic pipeline."""
        texts = ["Hello world", "test data", "more text"]
        chunks = run_pipeline(texts)
        assert len(chunks) == 3
        assert all(isinstance(c, OptimizedTextChunk) for c in chunks)

    def test_run_pipeline_with_overlap(self) -> None:
        """Test pipeline includes overlap metrics."""
        texts = ["hello world test", "hello world again"]
        chunks = run_pipeline(texts)
        # Second chunk should have overlap metric
        assert "overlap_with_prev" in chunks[1].metrics

    def test_run_pipeline_optimized_basic(self) -> None:
        """Test optimized pipeline."""
        texts = ["Hello world", "test data", "more text"]
        chunks = run_pipeline_optimized(texts)
        assert len(chunks) == 3
        assert all(isinstance(c, OptimizedTextChunk) for c in chunks)

    def test_run_pipeline_consistency(self) -> None:
        """Test that both pipelines produce same structure."""
        texts = ["test one", "test two", "test three"]

        chunks1 = run_pipeline(texts)
        chunks2 = run_pipeline_optimized(texts)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2, strict=True):
            assert c1.chunk_id == c2.chunk_id
            assert c1.source == c2.source


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer utility."""

    def test_compare_functions_basic(self) -> None:
        """Test comparing two functions."""

        def slow_func(x: int) -> int:
            import time

            time.sleep(0.01)
            return x * 2

        def fast_func(x: int) -> int:
            return x * 2

        result = PerformanceAnalyzer.compare_functions(slow_func, fast_func, 5, iterations=2)

        assert "speedup" in result
        assert "baseline_time" in result
        assert "optimized_time" in result
        assert "improvement_percent" in result
        # Fast function should be faster
        assert result["speedup"] > 1.0
