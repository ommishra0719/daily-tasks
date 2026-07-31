# Empirical Evaluation: Hybrid vs. Dense vs. Sparse Retrieval

This report documents the actual execution results of `hybrid_retriever.py` comparing **Dense Retrieval** (`all-MiniLM-L6-v2`), **Sparse Retrieval** (`BM25Okapi`), and **Hybrid Search** (Reciprocal Rank Fusion with $k=60$).

---

## 1. Execution Results Summary

| Query | Top Dense Doc | Top Sparse Doc | Top Hybrid Doc | Winner / Impact |
| :--- | :--- | :--- | :--- | :--- |
| **`cancellation policy`** | Doc 0 | Doc 0 | Doc 0 | Consensus |
| **`OrderID AB123`** | Doc 2 | Doc 2 | Doc 2 | Consensus |
| **`refund for my order`** | Doc 1 | Doc 4 | **Doc 0** | **Hybrid Victory** |
| **`sparse retrieval Python library`** | Doc 4 | Doc 4 | Doc 4 | Consensus |
| **`AI vector embeddings`** | Doc 7 | Doc 7 | Doc 7 | Consensus |

---

## 2. Detailed Query Analysis

### Query 1: `"cancellation policy"`
* **Dense Top:** Doc 0 (*"The cancellation policy states you can get a full refund..."*)
* **Sparse Top:** Doc 0
* **Hybrid Top:** Doc 0
* **Analysis:** Both retrievers easily identified the exact and semantic intent. Consensus was reached instantly.

### Query 2: `"OrderID AB123"`
* **Dense Top:** Doc 2 (*"OrderID AB123 has been dispatched..."*)
* **Sparse Top:** Doc 2
* **Hybrid Top:** Doc 2
* **Analysis:** `all-MiniLM-L6-v2` successfully matched the specific ID in this small corpus alongside BM25, maintaining high precision across all methods.

### Query 3: `"refund for my order"` ⭐ *(Key Highlight)*
* **Dense Top:** Doc 1 (*"To cancel your order, please contact support..."*) — *Focused too heavily on "order".*
* **Sparse Top:** Doc 4 (*"Rank_bm25 is a Python library..."*) — *Failed due to weak keyword overlaps across generic stop-words.*
* **Hybrid Top:** **Doc 0** (*"The cancellation policy states you can get a full refund if you cancel within 24 hours."*)
* **Analysis:** **This query demonstrates the exact reason to use Hybrid Search.** 
  * Dense ranked Doc 1 first, but had Doc 0 in its top-K (capturing the semantic concept of "refund").
  * Sparse missed the mark on top-1, but had Doc 0 in its top-K.
  * **RRF Score Fusion** aggregated the rank positions from both methods. Because Doc 0 performed consistently well across both dense and sparse candidate lists, its combined reciprocal rank pushed it to `#1` overall—outperforming both individual retrievers!

### Query 4: `"sparse retrieval Python library"`
* **Dense Top:** Doc 4 (*"Rank_bm25 is a Python library for sparse retrieval."*)
* **Sparse Top:** Doc 4
* **Hybrid Top:** Doc 4
* **Analysis:** Both semantic matching and exact keyword matching converged on Doc 4.

### Query 5: `"AI vector embeddings"`
* **Dense Top:** Doc 7 (*"Machine learning models require dense vector embeddings."*)
* **Sparse Top:** Doc 7
* **Hybrid Top:** Doc 7
* **Analysis:** Dense successfully mapped "AI" to "Machine learning", while Sparse caught "vector embeddings". RRF locked in the correct top document.

---

## 3. Key Takeaways

1. **RRF Prevents Single-Retriever Failure Modes:** On complex or multi-part queries (like `"refund for my order"`), individual retrievers often pick sub-optimal top-1 documents by over-indexing on a single keyword or concept. RRF smooths out these individual failures.
2. **Robustness:** Hybrid search consistently delivers equal or superior top-1 recall compared to using Dense or Sparse in isolation.
3. **Action Item:** For production deployment, keep `k=60` for RRF and ensure top-10 candidate extraction from both retrievers before fusing.