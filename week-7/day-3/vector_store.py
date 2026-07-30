import hashlib
from typing import Protocol, List, Dict, Any, Optional

# --- Chroma Imports ---
import chromadb

# --- Qdrant Imports ---
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)

class VectorStore(Protocol):
    """Abstract interface for a Vector Database in a RAG pipeline."""
    
    def add_documents(
        self, 
        doc_id: str, 
        texts: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Adds document chunks and their embeddings to the store."""
        ...

    def search(
        self, query_embedding: List[float], filter_dict: Optional[Dict[str, Any]] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Searches the store for the most similar chunks, optionally filtered by metadata."""
        ...

    def delete_document(self, doc_id: str) -> None:
        """Deletes all chunks associated with a specific document ID."""
        ...


class ChromaVectorStore:
    def __init__(self, collection_name: str = "docs", persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def _generate_chunk_ids(self, doc_id: str, num_chunks: int) -> List[str]:
        return [f"{doc_id}_chunk_{i}" for i in range(num_chunks)]

    def add_documents(
        self, doc_id: str, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]
    ) -> None:
        ids = self._generate_chunk_ids(doc_id, len(texts))
        # Ensure document_id is injected into metadata for easy deletion/filtering
        for meta in metadatas:
            meta["document_id"] = doc_id
            
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )

    def search(
        self, query_embedding: List[float], filter_dict: Optional[Dict[str, Any]] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict if filter_dict else None
        )
        
        parsed_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            # query returns a list of lists (one list per query vector)
            for text, meta in zip(results['documents'][0], results['metadatas'][0]):
                parsed_results.append({"text": text, "metadata": meta})
        return parsed_results

    def delete_document(self, doc_id: str) -> None:
        self.collection.delete(where={"document_id": doc_id})


class QdrantVectorStore:
    def __init__(self, collection_name: str = "docs", vector_size: int = 1536):
        self.collection_name = collection_name
        # Note: ":memory:" is used here for testing execution. 
        # For production, replace with QdrantClient(url="...") pointing to your Docker instance.
        self.client = QdrantClient(":memory:") 
        
        # Ensure collection exists
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

    def _generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        # Qdrant requires UUIDs or unsigned integers for IDs. Using an MD5 hash of deterministic string.
        hash_str = hashlib.md5(f"{doc_id}_chunk_{chunk_index}".encode()).hexdigest()
        # Convert hex to standard UUID format
        return f"{hash_str[:8]}-{hash_str[8:12]}-{hash_str[12:16]}-{hash_str[16:20]}-{hash_str[20:]}"

    def add_documents(
        self, doc_id: str, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]
    ) -> None:
        points = []
        for i, (text, emb, meta) in enumerate(zip(texts, embeddings, metadatas)):
            point_id = self._generate_chunk_id(doc_id, i)
            payload = meta.copy()
            payload["text"] = text
            payload["document_id"] = doc_id
            
            points.append(PointStruct(id=point_id, vector=emb, payload=payload))
            
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self, query_embedding: List[float], filter_dict: Optional[Dict[str, Any]] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        query_filter = None
        if filter_dict:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v)) 
                for k, v in filter_dict.items()
            ]
            query_filter = Filter(must=conditions)

        # NOTE: QdrantClient.search() is removed in newer qdrant-client versions.
        # query_points() is the current API; it returns a response object,
        # so we unwrap `.points` to get the actual hit list.
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=top_k
        )
        hits = response.points

        parsed_results = []
        for hit in hits:
            # Pop text out of payload to standardize output with Chroma
            payload = hit.payload.copy() if hit.payload else {}
            text = payload.pop("text", "")
            parsed_results.append({"text": text, "metadata": payload})
            
        return parsed_results

    def delete_document(self, doc_id: str) -> None:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=doc_id))]
            )
        )

# ==========================================
# TEST SUITE
# ==========================================
def run_test_suite(store: VectorStore):
    print(f"Testing {store.__class__.__name__}...")
    
    # 1. Add Documents
    doc_id = "doc_123"
    texts = ["This is chunk one about policies.", "This is chunk two published in 2023."]
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    metadatas = [{"doc_type": "policy", "year": 2022}, {"doc_type": "policy", "year": 2023}]
    
    store.add_documents(doc_id, texts, embeddings, metadatas)
    
    # 2. Search without filters
    results = store.search(query_embedding=[0.1, 0.2, 0.3], top_k=2)
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    
    # 3. Search with metadata filtering
    filtered_results = store.search(query_embedding=[0.4, 0.5, 0.6], filter_dict={"year": 2023}, top_k=2)
    assert len(filtered_results) == 1, f"Expected 1 result after filtering, got {len(filtered_results)}"
    assert filtered_results[0]["metadata"]["year"] == 2023, "Filter returned incorrect year."
    
    # 4. Delete document
    store.delete_document(doc_id)
    post_delete_results = store.search(query_embedding=[0.1, 0.2, 0.3], top_k=2)
    assert len(post_delete_results) == 0, "Document was not deleted successfully."
    
    print("All tests passed!\n")

if __name__ == "__main__":
    # Note: Ensure vector size matches test embeddings (size=3)
    chroma_store = ChromaVectorStore(collection_name="test_docs")
    qdrant_store = QdrantVectorStore(collection_name="test_docs", vector_size=3)
    
    run_test_suite(chroma_store)
    run_test_suite(qdrant_store)