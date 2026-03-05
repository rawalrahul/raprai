---
name: rag-pipeline-architect
description: "Design production-ready RAG systems with document ingestion, chunking strategies, embedding models, vector stores, retrieval tuning, and evaluation frameworks. Cover hybrid search, re-ranking, and faithfulness assessment."
category: ai-automation
difficulty: advanced
model_boost: "Fixes naive RAG implementations that retrieve irrelevant documents, hallucinate despite retrieval, and fail to scale to large document collections"
---

# RAG Pipeline Architect

## Purpose
This skill teaches you to build Retrieval-Augmented Generation (RAG) systems that reliably retrieve relevant context and ground model responses in real data. You'll design document ingestion pipelines, select chunking strategies, choose embedding and vector store technologies, tune retrieval, construct prompts, and evaluate output quality. The output is a production-ready RAG system that balances speed, cost, and accuracy.

## When to Use
- Building knowledge-grounded chatbots or search systems
- Ingesting large document collections (100K+ documents)
- Systems where hallucination is unacceptable (legal, medical, financial)
- Multi-source fact retrieval and synthesis
- Implementing semantic search over unstructured text
- **Do NOT use when**: Small knowledge base (<100 docs, can fit in context), real-time document updates not critical, or purely generative tasks without retrieval requirements

## Instructions

### Step 1: Document Ingestion Pipeline Design
Create a robust system to ingest, validate, and store documents.

**Ingestion Stages**:

**Stage 1: Acquisition & Format Parsing**
```python
# Supported formats with parsers
ingestion_config = {
    "pdf": {
        "library": "pdfplumber",  # Maintains layout, tables
        "extraction_method": "text_with_layout",
        "metadata_extraction": ["title", "author", "creation_date"],
        "handling": "extract per page + preserve page breaks"
    },
    "html": {
        "library": "BeautifulSoup4",
        "extraction_method": "semantic_tags (h1, p, table, code)",
        "skip_tags": ["script", "style", "nav"],
        "metadata_extraction": ["title", "meta description", "headers"]
    },
    "markdown": {
        "library": "markdown",
        "extraction_method": "section-aware (# headers become chunks)",
        "metadata_extraction": ["frontmatter (YAML)", "headers"]
    },
    "docx": {
        "library": "python-docx",
        "extraction_method": "paragraph-preserving",
        "metadata_extraction": ["core properties", "custom properties"]
    },
    "txt": {
        "library": "raw",
        "extraction_method": "split by double newlines",
        "metadata_extraction": ["filename", "modification date"]
    }
}

class DocumentIngestor:
    async def ingest(self, source: str, source_type: str, metadata: dict) -> list[Document]:
        """Parse document from file/URL/stream"""
        parser = PARSERS[source_type]
        raw_text = await parser.parse(source)

        # Extract structured metadata
        doc_metadata = {
            "source": source,
            "source_type": source_type,
            "ingestion_timestamp": now(),
            "version": metadata.get("version", "1.0"),
            "hash": hashlib.sha256(raw_text.encode()).hexdigest()  # Detect duplicates
        }

        return Document(
            id=generate_uuid(),
            content=raw_text,
            metadata=doc_metadata
        )
```

**Stage 2: Validation & Cleaning**
```python
class DocumentValidator:
    async def validate(self, doc: Document) -> tuple[bool, list[str]]:
        """Check document quality before indexing"""
        issues = []

        # Check length
        if len(doc.content) < 10:
            issues.append("Document too short (< 10 characters)")

        # Check language (assume English)
        detected_lang = detect_language(doc.content)
        if detected_lang != "en":
            issues.append(f"Non-English content detected: {detected_lang}")

        # Check for PII (privacy concern)
        pii_detected = detect_pii(doc.content)
        if pii_detected:
            issues.append(f"PII detected: {', '.join(pii_detected)}")
            # Option: mask PII or reject document

        # Check for duplicates (by content hash)
        existing = await db.query("documents", {"hash": doc.metadata['hash']})
        if existing:
            issues.append(f"Duplicate of document {existing[0]['id']}")

        is_valid = len(issues) == 0
        return is_valid, issues
```

**Stage 3: Storage & Indexing**
```python
class DocumentStore:
    async def store_and_index(self, doc: Document):
        """Store original document + create index pointers"""

        # Store full document in cold storage (cheap)
        await storage.put(
            bucket="documents",
            key=f"{doc.id}/content.txt",
            value=doc.content,
            metadata=doc.metadata
        )

        # Create database record with metadata
        await db.insert("documents", {
            "id": doc.id,
            "source": doc.metadata["source"],
            "hash": doc.metadata["hash"],
            "size_bytes": len(doc.content),
            "ingestion_timestamp": doc.metadata["ingestion_timestamp"],
            "last_updated": now(),
            "status": "indexed"
        })

        return doc.id
```

**Ingestion Monitoring**:
```yaml
metrics:
  documents_ingested_total: Counter
  ingestion_errors: Counter[error_type, source_type]
  validation_failures: Counter[failure_reason]
  duplicate_detection_rate: Gauge (% of incoming docs that are duplicates)
  average_document_size: Histogram (bytes)
  ingestion_latency_ms: Histogram
```

### Step 2: Chunking Strategies
Break documents into retrieval-sized pieces; wrong chunking destroys RAG quality.

**Strategy 1: Fixed-Size Chunking** (simple, baseline)
```python
class FixedSizeChunker:
    def chunk(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
        """
        Split text into fixed-size chunks with overlap

        Args:
            chunk_size: Target chunk size in characters
            overlap: Overlap between consecutive chunks (preserves context)

        Returns:
            List of chunk strings
        """
        chunks = []
        stride = chunk_size - overlap

        for i in range(0, len(text), stride):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk.strip())

        return chunks

# Example:
chunker = FixedSizeChunker()
text = "Document about machine learning..."
chunks = chunker.chunk(text, chunk_size=500, overlap=50)
# Result: ["Document about machine learning...", "about machine learning... neural networks...", ...]

# Pros: Simple, fast, predictable token count
# Cons: Ignores semantic boundaries (may cut sentences mid-way)
```

**Strategy 2: Semantic Chunking** (respect sentence/paragraph boundaries)
```python
class SemanticChunker:
    def chunk(self, text: str, target_size: int = 500) -> list[str]:
        """
        Chunk by sentences/paragraphs, aiming for target size

        Preserves semantic boundaries
        """
        # Split by paragraph first
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            sentences = sent_tokenize(para)  # nltk.tokenize

            for sentence in sentences:
                # Check if adding sentence exceeds target
                if len(current_chunk) + len(sentence) > target_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

# Pros: Respects document structure, fewer cut-off sentences
# Cons: Chunks may vary greatly in size
```

**Strategy 3: Recursive Chunking** (best for code/markdown)
```python
class RecursiveChunker:
    def chunk(self, text: str, separators: list = None, chunk_size: int = 1000) -> list[str]:
        """
        Recursively split by separators until chunks are small enough

        Useful for code (split by function), markdown (split by headers)
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", " ", ""]

        def split_text(text: str, separators: list) -> list[str]:
            good_splits = []

            for separator in separators:
                if separator in text:
                    splits = text.split(separator)
                    # Recursively split if any piece is too large
                    good_splits = [
                        s for split in splits
                        if (s := split) and len(s) < chunk_size
                    ]
                    if good_splits:
                        break

            if not good_splits:
                # If no separator works, return text as-is
                return [text] if text else []

            # Merge small chunks to reach target size
            return self.merge_splits(good_splits, chunk_size, separator)

        return split_text(text, separators)

    def merge_splits(self, splits: list, chunk_size: int, separator: str) -> list[str]:
        """Combine small chunks back together"""
        merged = []
        current = ""

        for split in splits:
            if len(current) + len(split) <= chunk_size:
                current += separator + split
            else:
                if current:
                    merged.append(current)
                current = split

        if current:
            merged.append(current)

        return merged

# Example: Markdown document
text = """
# Section 1
## Subsection 1.1
Content here...

## Subsection 1.2
More content...

# Section 2
Different content...
"""
chunker = RecursiveChunker()
chunks = chunker.chunk(text, chunk_size=500)
# Result: Chunks respect header hierarchy
```

**Metadata Preservation During Chunking**:
```python
class ChunkWithMetadata:
    def __init__(self, content: str, doc_id: str, chunk_index: int,
                 chunk_header: str = None, chunk_context: str = None):
        self.content = content
        self.doc_id = doc_id
        self.chunk_index = chunk_index
        self.chunk_header = chunk_header  # Section title (e.g., "Chapter 5: ML Basics")
        self.chunk_context = chunk_context  # Previous chunk summary
        self.tokens = count_tokens(content)

# When retrieving, include metadata to provide context to LLM:
# "Found in: {chunk_header} | Document: {doc_id} | Relevance: {score}"
```

**Chunking Strategy Comparison**:
| Strategy | Pros | Cons | Best For |
|----------|------|------|----------|
| Fixed-size | Simple, predictable tokens | Ignores semantics | Baseline, homogenous docs |
| Semantic | Respects boundaries | Variable size | Most documents (default) |
| Recursive | Handles nested structure | Complex logic | Code, markdown, structured docs |
| Sliding window | Preserves context | Expensive | Sliding-scale similarity |

### Step 3: Embedding Model Selection
Choose model based on speed, quality, and cost tradeoffs.

**Embedding Models** (2024):
```yaml
models:
  sentence-transformers/all-MiniLM-L6-v2:
    dimensions: 384
    speed: 370ms per 1K tokens (CPU)
    size: 22MB
    training_data: MNLI, STS, etc.
    strength: "Fast, accurate for general domain"
    best_for: "High-volume, latency-sensitive, limited GPU"
    cost: "$0 (open source)"

  sentence-transformers/all-mpnet-base-v2:
    dimensions: 768
    speed: 850ms per 1K tokens (CPU)
    size: 438MB
    training_data: Large-scale paired data
    strength: "Higher quality, general domain"
    best_for: "Standard production RAG"
    cost: "$0 (open source)"

  OpenAI text-embedding-3-small:
    dimensions: 1536
    speed: 2s per 1K tokens (API)
    cost: "$0.02 per 1M tokens"
    training_data: "Proprietary, large-scale"
    strength: "State-of-the-art quality, multilingual"
    best_for: "Quality-critical, multilingual, can afford API cost"

  Jina Embeddings:
    dimensions: 768
    max_length: 8192 tokens (vs 512 for most)
    cost: "$0.02 per 1M tokens"
    strength: "Long context, handles full documents"
    best_for: "Documents that don't fit in 512 tokens"

  Cohere Embed v3:
    dimensions: 1024
    cost: "$0.10 per 1M tokens"
    strength: "Domain-specific models available"
    best_for: "Financial, legal, scientific documents"
```

**Selection Decision Tree**:
```
Q1: Document volume and query rate?
├─ < 1000 docs, < 100 QPS
│  └─ Use sentence-transformers (free, no API cost)
├─ 1000-100K docs, 100-1000 QPS
│  └─ Use sentence-transformers with GPU acceleration
└─ > 100K docs, > 1000 QPS
   └─ Use OpenAI/Jina API (managed scaling)

Q2: Language coverage needed?
├─ English only
│  └─ sentence-transformers/all-MiniLM (smallest)
├─ Multiple languages
│  └─ OpenAI text-embedding-3 or multilingual models
└─ 100+ languages
   └─ Use OpenAI

Q3: Long documents?
├─ <= 512 tokens
│  └─ Any model works
├─ 512-8000 tokens
│  └─ Jina Embeddings (8K context)
└─ > 8000 tokens
   └─ Split further before embedding

Q4: Budget per 1M tokens?
├─ $0 (open source acceptable)
│  └─ sentence-transformers
├─ < $1
│  └─ OpenAI text-embedding-3 ($0.02)
└─ > $1
   └─ Cohere or specialized models
```

**Embedding Implementation**:
```python
class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed single text"""
        embedding = self.model.encode(text, convert_to_tensor=True)
        return embedding.cpu().numpy()

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[np.ndarray]:
        """Embed multiple texts efficiently"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=False
        )
        return embeddings

# Usage:
embedder = EmbeddingService()
chunk_embeddings = await embedder.embed_batch(chunks, batch_size=64)
# Result: (num_chunks, 384) array
```

### Step 4: Vector Store Selection and Configuration
Choose where to store and query embeddings.

**Vector Store Comparison**:
```yaml
pinecone:
  managed: true  # Fully managed cloud
  regions: "50+ global regions"
  indexing_type: ["approximate (HNSW)", "exact_search"]
  slas: "99.9% uptime"
  pricing: "$0.04/1M vectors + $0.25/hour for pod"
  best_for: "Serverless, global scale, minimal ops"
  tradeoff: "Higher cost, vendor lock-in"

weaviate:
  managed: "Self-hosted or cloud"
  indexing_type: ["HNSW", "product quantization"]
  hybrid_search: "Built-in BM25 + vector search"
  cost: "Self-hosted (free) or $25/month cloud"
  best_for: "Hybrid search, full control, cost-conscious"

pgvector:
  database: "PostgreSQL extension"
  indexing_type: ["IVFFlat", "HNSW"]
  cost: "PostgreSQL hosting cost (Supabase ~$25/month)"
  best_for: "Relational data + vectors, SQL integration"
  tradeoff: "Manage infrastructure, slower for scale"

chroma:
  type: "Lightweight, in-memory"
  indexing: "Approximate nearest neighbor"
  cost: "$0 (open source)"
  best_for: "Development, small collections (<10M vectors)"
  tradeoff: "Limited scale, no persistence by default"

faiss:
  type: "Facebook's open-source library"
  indexing: ["Flat", "IVF", "HNSW"]
  cost: "$0 (open source)"
  best_for: "Offline indexing, research"
  tradeoff: "No built-in HTTP API, self-manage deployment"
```

**Vector Store Configuration**:
```python
# Pinecone example
import pinecone

class VectorStore:
    def __init__(self, index_name: str = "documents"):
        pinecone.init(api_key="...", environment="us-west1-gcp")

        # Create index if not exists
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=index_name,
                dimension=384,  # Match embedding dimension
                metric="cosine",  # or "euclidean", "dotproduct"
                pod_type="s1.x2"  # 2 replicas for HA
            )

        self.index = pinecone.Index(index_name)

    async def upsert_vectors(self, vectors: list[tuple[str, list[float], dict]]):
        """Store vectors with metadata"""
        # Format: (id, embedding, metadata)
        self.index.upsert(vectors=vectors)

    async def query(self, query_embedding: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        """Find nearest neighbors"""
        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True
        )
        return [(match.id, match.score, match.metadata) for match in results.matches]

    async def delete(self, ids: list[str]):
        """Delete vectors by ID"""
        self.index.delete(ids=ids)
```

### Step 5: Retrieval Tuning (top-k, MMR, re-ranking)
Optimize what gets returned to the LLM.

**Simple Top-K Retrieval**:
```python
async def retrieve_simple(self, query: str, top_k: int = 5) -> list[str]:
    """Return top K most similar chunks"""
    query_embedding = await embedder.embed_text(query)
    results = await vector_store.query(query_embedding, top_k=top_k)
    # Results: [(chunk_id, similarity_score, metadata), ...]
    return [chunk_id for chunk_id, score, _ in results]
```

**Maximum Marginal Relevance (MMR)** (diversity + relevance):
```python
async def retrieve_mmr(self, query: str, top_k: int = 5, lambda_param: float = 0.5) -> list[str]:
    """
    Return top K results balancing relevance and diversity
    Avoids redundant similar chunks

    MMR = argmax_i [lambda * relevance(i, query) - (1-lambda) * similarity(i, already_selected)]
    """
    query_embedding = await embedder.embed_text(query)

    # Get more candidates than needed
    candidates = await vector_store.query(query_embedding, top_k=top_k * 3)

    selected = []
    candidate_embeddings = [embed(cand[0]) for cand in candidates]

    for _ in range(top_k):
        best_idx = None
        best_score = -1

        for i, (cand_id, relevance, meta) in enumerate(candidates):
            if i in selected:
                continue

            # Relevance to query
            relevance_score = relevance

            # Minimum dissimilarity to already selected
            min_similarity = 0
            if selected:
                selected_embeddings = [candidate_embeddings[j] for j in selected]
                similarities = [
                    cosine_similarity(candidate_embeddings[i], s)
                    for s in selected_embeddings
                ]
                min_similarity = max(similarities)

            mmr_score = lambda_param * relevance_score - (1 - lambda_param) * min_similarity

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        selected.append(best_idx)

    return [candidates[i][0] for i in selected]

# Usage:
# lambda=1.0: Pure relevance (all similar chunks)
# lambda=0.5: Balance relevance and diversity (default)
# lambda=0.0: Pure diversity (only dissimilar chunks)
```

**Re-Ranking** (improve retrieval quality):
```python
from sentence_transformers import CrossEncoder

class ReRanker:
    def __init__(self):
        # Cross-encoder: scores query-document relevance
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

    async def rerank(self, query: str, candidates: list[str], top_k: int = 5) -> list[str]:
        """
        Re-rank candidates using cross-encoder
        More expensive than embedding similarity, but more accurate
        """
        # Cross-encoder takes (query, document) pairs
        pairs = [(query, doc) for doc in candidates]
        scores = self.model.predict(pairs)

        # Sort by cross-encoder score
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in ranked[:top_k]]

# Usage in full pipeline:
query_embedding = await embedder.embed_text(query)
candidates = await vector_store.query(query_embedding, top_k=20)  # Get more
reranked = await reranker.rerank(query, candidates, top_k=5)  # Re-rank to top 5
```

**Hybrid Search** (keyword + semantic):
```python
async def retrieve_hybrid(self, query: str, top_k: int = 5) -> list[str]:
    """
    Combine BM25 (keyword) and vector (semantic) search
    Better recall, especially for specific terms
    """
    # Semantic search
    query_embedding = await embedder.embed_text(query)
    semantic_results = await vector_store.query(query_embedding, top_k=top_k * 2)

    # Keyword search (BM25)
    keyword_results = await bm25_index.search(query, top_k=top_k * 2)

    # Merge and deduplicate, prioritizing high scores
    merged = {}
    for doc_id, score in semantic_results:
        merged[doc_id] = merged.get(doc_id, 0) + score * 0.6

    for doc_id, score in keyword_results:
        merged[doc_id] = merged.get(doc_id, 0) + score * 0.4

    # Return top K by combined score
    ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, score in ranked[:top_k]]
```

### Step 6: Prompt Construction with Retrieved Context
Format retrieved documents into effective LLM prompts.

**Template-Based Prompt Construction**:
```python
class RAGPromptConstructor:
    TEMPLATE = """
    You are a helpful assistant. Answer the user's question based on the provided context.
    If you cannot find the answer in the context, say "I don't know" rather than guessing.

    Context:
    {context}

    Question: {question}

    Answer:
    """

    def construct_prompt(self, question: str, retrieved_docs: list[str]) -> str:
        """Build final prompt with question + context"""

        # Format retrieved documents with metadata
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[Source {i}]: {doc}")

        context = "\n\n".join(context_parts)

        # Build prompt
        prompt = self.TEMPLATE.format(
            context=context,
            question=question
        )

        return prompt

    def construct_prompt_with_citations(self, question: str,
                                       retrieved_docs: list[dict]) -> str:
        """Build prompt with source citations"""
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(
                f"[Source {i}: {doc.get('metadata', {}).get('source', 'Unknown')}]\n"
                f"{doc['content']}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""Based on the following sources, answer the question.
        Be sure to cite which source(s) you used.

        {context}

        Question: {question}

        Answer (with citations):
        """
        return prompt
```

**Controlling Context Window**:
```python
class ContextWindowManager:
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens

    def select_documents(self, documents: list[tuple[str, float]],
                        question: str) -> list[str]:
        """
        Select documents that fit within token budget
        Prioritize high relevance + low redundancy
        """
        selected = [f"Question: {question}"]  # Start with question
        used_tokens = count_tokens(" ".join(selected))

        for doc, relevance_score in documents:
            doc_tokens = count_tokens(doc)

            # Check if adding this doc would exceed limit
            if used_tokens + doc_tokens <= self.max_tokens:
                selected.append(doc)
                used_tokens += doc_tokens
            else:
                break  # Stop when budget exhausted

        return selected[1:]  # Return docs only (not question)

# Usage:
context_docs = select_documents(
    retrieved_docs_with_scores,
    query,
    max_tokens=2000
)
```

### Step 7: Evaluation Framework
Measure RAG quality across multiple dimensions.

**Evaluation Metrics**:
```python
from langchain.evaluation import QAEvalChain

class RAGEvaluator:
    def __init__(self):
        self.qa_eval = QAEvalChain.from_llm(llm=ChatOpenAI())

    async def evaluate_faithfulness(self, context: str, response: str) -> float:
        """
        Check if response is supported by context (not hallucinated)
        Score: 0-1 (1 = fully faithful, 0 = unsupported)
        """
        prompt = f"""
        Context: {context}

        Claimed answer: {response}

        Is this answer fully supported by the context? (Yes/No/Partially)
        Explain why.
        """

        evaluation = await self.qa_eval.arun(
            query=prompt,
            answer=response,
            question=""
        )

        # Parse response to extract score
        return extract_score(evaluation)

    async def evaluate_relevance(self, question: str, response: str) -> float:
        """Check if response answers the question"""
        prompt = f"""
        Question: {question}
        Response: {response}

        Does this response adequately answer the question? (0-10)
        """
        score = await llm.acomplete(prompt)
        return float(score) / 10.0

    async def evaluate_retrieval_quality(self, question: str,
                                        retrieved_docs: list[str],
                                        expected_doc_ids: list[str]) -> dict:
        """
        Check if correct documents were retrieved
        (Requires gold standard annotations)
        """
        retrieved_ids = [doc.metadata['id'] for doc in retrieved_docs]

        tp = len(set(retrieved_ids) & set(expected_doc_ids))  # True positives
        fp = len(set(retrieved_ids) - set(expected_doc_ids))  # False positives
        fn = len(set(expected_doc_ids) - set(retrieved_ids))  # False negatives

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "mrr": compute_mrr(retrieved_ids, expected_doc_ids)
        }
```

**Test Dataset Construction** (gold standard):
```yaml
evaluation_set:
  size: 100 questions
  format:
    - question: "What is RAG?"
      expected_sources: ["doc_id_1", "doc_id_5"]
      expected_answer: "RAG combines retrieval with generation..."
      difficulty: "easy"

    - question: "Compare embeddings from 2024"
      expected_sources: ["doc_id_12", "doc_id_45"]
      expected_answer: "..."
      difficulty: "hard"

  metrics_to_track:
    retrieval_precision: >= 0.85 (correct docs retrieved)
    retrieval_recall: >= 0.80 (don't miss relevant docs)
    faithfulness: >= 0.90 (answer not hallucinated)
    relevance: >= 0.80 (answer matches question)
    latency_p99: < 5000ms (end-to-end retrieval + LLM)
```

## Output Template

**RAG System Design Document**:
```markdown
# [Domain] RAG System Architecture

## Overview
[Purpose, use cases, constraints]

## Document Ingestion
[Sources, frequency, validation rules]

## Chunking Strategy
[Strategy type, chunk size, overlap, metadata preserved]

## Embedding Model
[Model name, dimensions, speed, cost]

## Vector Store
[Storage choice, indexing config, region/HA]

## Retrieval Strategy
[top-k, MMR, re-ranking, hybrid search]

## Evaluation Results
[Precision/recall/F1, faithfulness, latency]

## Cost Estimation
[Per query cost, monthly spend for expected volume]
```

## Quality Gates

1. **Retrieval Precision >= 0.85**: % of retrieved docs relevant to query
2. **Retrieval Recall >= 0.80**: % of relevant docs actually retrieved
3. **Faithfulness >= 0.90**: % of answers supported by context
4. **Relevance >= 0.80**: % of answers addressing user question
5. **Latency P99 <= 5s**: End-to-end retrieval + LLM generation
6. **Cost per query <= budget**: Embedding + vector store + LLM token cost
7. **Duplicate removal**: No identical chunks indexed

## Examples

### Good RAG: Financial Document Q&A
```
Documents: 10K SEC filings (revenue, expenses, risk factors)
Chunking: Recursive by section (preserves "Risk Factors" section)
Embedding: OpenAI text-embedding-3 (multilingual, high quality)
Vector Store: Pinecone (99.9% uptime SLA)
Retrieval: Hybrid (BM25 for ticker references + vector for semantic)
Re-ranking: Cross-encoder for financial relevance
Prompt: Include source citation for compliance

Results:
- Retrieval precision: 0.92
- Faithfulness: 0.95 (financial accuracy critical)
- Query latency: 2.3s (P99)
✓ Production ready
```

## Common Mistakes

1. **Wrong Chunking Size / No Context**
   - ❌ Chunks 100 chars (too small) → Context lost
   - ✓ Use 400-1000 chars with 50-100 char overlap
   - ✓ Preserve semantic boundaries (end of sentences, paragraphs)

2. **Naive Top-K Retrieval / Redundancy**
   - ❌ Top-5 retrieval returns 5 nearly identical chunks
   - ✓ Use MMR to diversify, or eliminate duplicates pre-indexing

3. **Hallucination Despite Retrieved Docs**
   - ❌ "Based on these documents... the answer is X" (X not in docs)
   - ✓ Use faithfulness evaluation, fine-tune with retrieval-grounded examples

4. **No Cost Control / Surprise Bills**
   - ❌ Embedding every document update = $100+ monthly
   - ✓ Batch embeddings, incremental indexing, deduplication

5. **Evaluation on Training Data Only**
   - ❌ Test on same documents used in indexing
   - ✓ Split into train/val/test; evaluate on holdout set

## Anti-Patterns

1. **All-In-One Embedding (Ignore Fine-Tuning)**
   - ❌ Use generic embedding for domain-specific docs (law, medicine)
   - ✓ Consider domain-specific models or fine-tuning
   - Impact: Worse retrieval quality

2. **Vector Store Without Backup**
   - ❌ Single region Pinecone instance
   - ✓ Multi-region replication, regular backups
   - Impact: Data loss on outage

3. **Prompt Injection / Untrusted Context**
   - ❌ Retrieved documents can contain malicious prompts
   - ✓ Sanitize document content, use system prompts to lock behavior
   - Impact: Model jailbreak via retrieved documents
