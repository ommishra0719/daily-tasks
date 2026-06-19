import pytest
from unittest.mock import Mock, AsyncMock

from chunker_strategy import (
    FixedSizeChunker,
    SentenceChunker,
    RecursiveChunker,
    DocumentProcessor,
    ChunkerStrategy,
)


# ------------------------------------------------
# Fixtures
# ------------------------------------------------

@pytest.fixture
def fixed_chunker():
    return FixedSizeChunker(chunk_size=5)


@pytest.fixture
def sentence_chunker():
    return SentenceChunker()


@pytest.fixture
def recursive_chunker():
    return RecursiveChunker(max_length=10)


# ------------------------------------------------
# FixedSizeChunker tests
# ------------------------------------------------

@pytest.mark.parametrize(
    "text,size,expected",
    [
        ("abcdefghij", 5, ["abcde", "fghij"]),
        ("abcdefghi", 4, ["abcd", "efgh", "i"]),
        ("abc", 10, ["abc"]),
        ("a", 1, ["a"]),
    ]
)
def test_fixed_size_chunking(text, size, expected):
    chunker = FixedSizeChunker(size)

    result = chunker.chunk(text)

    assert result == expected


def test_fixed_chunker_empty_string():
    chunker = FixedSizeChunker(5)

    assert chunker.chunk("") == []


def test_fixed_chunker_none_like_false_value():
    chunker = FixedSizeChunker()

    assert chunker.chunk(None) == []


# ------------------------------------------------
# SentenceChunker tests
# ------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Hello. World!",
            ["Hello.", "World!"]
        ),
        (
            "One? Two! Three.",
            ["One?", "Two!", "Three."]
        ),
        (
            "Single sentence",
            ["Single sentence"]
        ),
    ]
)
def test_sentence_chunker(text, expected, sentence_chunker):
    assert sentence_chunker.chunk(text) == expected


def test_sentence_chunker_empty():
    chunker = SentenceChunker()

    assert chunker.chunk("") == []


def test_sentence_chunker_removes_whitespace():
    chunker = SentenceChunker()

    result = chunker.chunk("   Hello. World!   ")

    assert result == ["Hello.", "World!"]


# ------------------------------------------------
# RecursiveChunker tests
# ------------------------------------------------

def test_recursive_chunker_short_text():
    chunker = RecursiveChunker(max_length=100)

    assert chunker.chunk("hello") == ["hello"]


def test_recursive_chunker_empty_string():
    chunker = RecursiveChunker()

    assert chunker.chunk("") == []


def test_recursive_chunker_paragraph_split():
    text = "abc\n\ndef"

    chunker = RecursiveChunker(max_length=3)

    assert chunker.chunk(text) == ["abc", "def"]


def test_recursive_chunker_sentence_split():
    text = "hello world. another sentence"

    chunker = RecursiveChunker(max_length=10)

    result = chunker.chunk(text)

    assert result == [
        "hello",
        "world",
        "another",
        "sentence"
    ]

def test_recursive_chunker_word_split():
    text = "one two three four"

    chunker = RecursiveChunker(max_length=4)

    result = chunker.chunk(text)

    assert result == ["one", "two", "three", "four"]


def test_recursive_chunker_exhausts_all_separators():
    text = "averyveryverylongword"

    chunker = RecursiveChunker(max_length=3)

    result = chunker.chunk(text)

    assert result == ["averyveryverylongword"]


# ------------------------------------------------
# DocumentProcessor tests
# ------------------------------------------------

def test_document_processor_delegates():
    mock_strategy = Mock(spec=ChunkerStrategy)
    mock_strategy.chunk.return_value = ["x"]

    processor = DocumentProcessor(mock_strategy)

    result = processor.process_document("hello")

    mock_strategy.chunk.assert_called_once_with("hello")
    assert result == ["x"]


def test_runtime_strategy_swap():
    processor = DocumentProcessor(FixedSizeChunker(3))

    processor.set_strategy(SentenceChunker())

    result = processor.process_document("A. B.")

    assert result == ["A.", "B."]


# ------------------------------------------------
# Mock test
# ------------------------------------------------

def test_mock_strategy_called():
    strategy = Mock(spec=ChunkerStrategy)
    strategy.chunk.return_value = ["mocked"]

    processor = DocumentProcessor(strategy)

    result = processor.process_document("data")

    strategy.chunk.assert_called_once()

    assert result == ["mocked"]


# ------------------------------------------------
# Async test
# ------------------------------------------------

@pytest.mark.asyncio
async def test_async_mock():
    fake_client = AsyncMock()

    fake_client.fetch.return_value = ["chunk1"]

    result = await fake_client.fetch()

    assert result == ["chunk1"]