import abc
import re
from typing import List

# ---------------------------------------------------------
# 1. Strategy Interface
# ---------------------------------------------------------
class ChunkerStrategy(abc.ABC):
    #The common interface for all chunking strategies. Any new chunker must implement the 'chunk' method.
    @abc.abstractmethod
    def chunk(self, text: str) -> List[str]:
        pass

# ---------------------------------------------------------
# 2. Concrete Strategies
# ---------------------------------------------------------
class FixedSizeChunker(ChunkerStrategy):
    #Chunks text into strict fixed-character sizes.
    
    def __init__(self, chunk_size: int = 100):
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> List[str]:
        if not text:
            return []
        return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]


class SentenceChunker(ChunkerStrategy):
    #Chunks text by sentences using basic punctuation splitting.
    
    def chunk(self, text: str) -> List[str]:
        if not text:
            return []
        # Split by . ! or ? followed by a space
        sentences = re.split(r'(?<=[.!?]) +', text.strip())
        return [s for s in sentences if s]


class RecursiveChunker(ChunkerStrategy):
    #Recursively splits text by decreasingly large separators until the chunk is under the max_length.
    
    def __init__(self, max_length: int = 50):
        self.max_length = max_length
        # Hierarchy of separators: Paragraphs, Sentences, Words
        self.separators = ["\n\n", ". ", " "]

    def chunk(self, text: str) -> List[str]:
        return self._split_recursively(text, 0)

    def _split_recursively(self, text: str, sep_index: int) -> List[str]:
        # Base case: if it's short enough, or we ran out of separators, return as is
        if len(text) <= self.max_length or sep_index >= len(self.separators):
            return [text] if text else []

        separator = self.separators[sep_index]
        splits = text.split(separator)
        
        final_chunks = []
        for split in splits:
            if len(split) <= self.max_length:
                # Add back the separator if it's not a newline for readability (simplified)
                final_chunks.append(split)
            else:
                # Recursively split this larger chunk with the next separator
                final_chunks.extend(self._split_recursively(split, sep_index + 1))
                
        return [c for c in final_chunks if c]

# ---------------------------------------------------------
# 3. Context / Client Class
# ---------------------------------------------------------
class DocumentProcessor:
    # The Context class. It doesn't know HOW text is chunked, only that its strategy object has a .chunk() method.
    
    def __init__(self, chunker: ChunkerStrategy):
        self._chunker = chunker

    # Allow changing strategy at runtime
    def set_strategy(self, chunker: ChunkerStrategy):
        self._chunker = chunker

    def process_document(self, text: str) -> List[str]:
        # Delegate the work to the injected strategy
        return self._chunker.chunk(text)

# ---------------------------------------------------------
# 4. Test Suite / Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    sample_text = (
        "Design patterns are great. They make code modular. "
        "Here is a second paragraph.\n\n"
        "It contains some much longer sentences that might need to be split up recursively if they exceed our maximum character length constraint."
    )

    print("--- Original Text ---")
    print(sample_text, "\n")

    # 1. Using Fixed Size Chunker
    processor = DocumentProcessor(FixedSizeChunker(chunk_size=40))
    print("--- Fixed Size Chunker (40 chars) ---")
    for i, c in enumerate(processor.process_document(sample_text)):
        print(f"Chunk {i+1}: {repr(c)}")

    # 2. Swapping to Sentence Chunker (Runtime swap, no change to client interface!)
    processor.set_strategy(SentenceChunker())
    print("\n--- Sentence Chunker ---")
    for i, c in enumerate(processor.process_document(sample_text)):
        print(f"Chunk {i+1}: {repr(c)}")

    # 3. Swapping to Recursive Chunker
    processor.set_strategy(RecursiveChunker(max_length=60))
    print("\n--- Recursive Chunker (max 60 chars) ---")
    for i, c in enumerate(processor.process_document(sample_text)):
        print(f"Chunk {i+1}: {repr(c)}")
