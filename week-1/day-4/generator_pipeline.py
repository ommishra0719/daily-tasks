from itertools import islice
from memory_profiler import profile
from pathlib import Path

def read_lines(file_path):
    # Read the file lazily, one line at a time
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            yield line


def clean_lines(lines):
    # Strip whitespace and skip blank lines
    for line in lines:
        cleaned = line.strip()

        if cleaned:
            yield cleaned


def chunk_lines(cleaned_lines, chunk_size):
    # Yield chunks containing chunk_size lines
    iterator = iter(cleaned_lines)

    while True:
        chunk = list(islice(iterator, chunk_size))

        if not chunk:
            break

        yield chunk


def document_pipeline(file_path, chunk_size):
    # Build the complete generator pipeline
    lines = read_lines(file_path)
    cleaned_lines = clean_lines(lines)

    yield from chunk_lines(cleaned_lines, chunk_size)


@profile
def process_file(file_path, chunk_size=100):
    total_chunks = 0

    for chunk in document_pipeline(file_path, chunk_size):
        # Simulate processing each chunk
        total_chunks += 1

    print(f"Processed {total_chunks} chunks")


if __name__ == "__main__":
    current_dir = Path(__file__).parent
    file_path = current_dir / "large_document.txt"

    process_file(file_path)