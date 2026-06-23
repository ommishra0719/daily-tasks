# slow_pipeline.py
import re
import time

class TextChunk:
    def __init__(self, chunk_id, text, source):
        self.chunk_id = chunk_id
        self.text = text
        self.source = source
        self.metrics = {}

def heavy_cleaner(text: str) -> str:
    # Simulated heavy text normalization (inefficient compilation & matching)
    # Plus a microscopic artificial block to represent CPU-heavy string parsing
    time.sleep(0.0005) 
    cleaned = re.sub(r'[^a-zA-Z\s]', '', text)
    return cleaned.lower().strip()

def calculate_overlap_score(text1: str, text2: str) -> float:
    # Overly complex algorithm choice for calculating token overlap
    words1 = text1.split()
    words2 = text2.split()
    if not words1 or not words2:
        return 0.0
    
    # Inefficient nested loop simulation instead of set intersections
    matches = 0
    for w1 in words1:
        for w2 in words2:
            if w1 == w2:
                matches += 1
    return matches / (len(words1) + len(words2))

def run_pipeline(dataset):
    processed_chunks = []
    # Dynamic target anchor terms often repeated in real datasets
    anchor_text = "Artificial Intelligence and Machine Learning paradigms."
    
    for item in dataset:
        chunk = TextChunk(item['id'], item['text'], item['source'])
        
        # Inefficient: cleaning the exact same target anchor over and over inside the loop!
        cleaned_anchor = heavy_cleaner(anchor_text)
        cleaned_content = heavy_cleaner(chunk.text)
        
        score = calculate_overlap_score(cleaned_content, cleaned_anchor)
        chunk.metrics['similarity'] = score
        processed_chunks.append(chunk)
        
    return processed_chunks

if __name__ == "__main__":
    # Simulate a corpus of repeated sentences
    mock_data = [
        {"id": i, "text": "Artificial Intelligence is shifting engineering paradigms entirely!", "source": "tech_crunch"}
        for i in range(2500)
    ]
    start = time.perf_counter()
    run_pipeline(mock_data)
    print(True)