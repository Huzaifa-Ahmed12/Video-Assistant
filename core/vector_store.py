import os
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}
    )

def build_vector_store(transcript: str) -> Chroma:
    print("Creating Vector Store......")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_text(transcript)
    docs = [
        Document(page_content=chunk, metadata={"chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]
    embeddings = get_embeddings()
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR
    )
    return vector_store

def load_vector_store() -> Chroma:
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    return vector_store

def get_documents_from_vector_store(vector_store: Chroma) -> List[Document]:
    """Extracts indexed Document objects from a Chroma vector store instance."""
    try:
        data = vector_store.get()
        texts = data.get("documents", [])
        metadatas = data.get("metadatas", [])
        return [
            Document(page_content=text, metadata=meta or {})
            for text, meta in zip(texts, metadatas)
        ]
    except Exception:
        return []

def get_retriever(
    vector_store: Chroma,
    docs: Optional[List[Document]] = None,
    weights: List[float] = [0.5, 0.5],
    k: int = 5
):
    """
    Creates a Hybrid Retriever combining BM25 keyword search and Dense Vector similarity search.
    
    :param vector_store: Chroma vector store instance
    :param docs: Optional list of Document objects. Extracted automatically from vector_store if None.
    :param weights: Weights for [BM25 keyword search, Dense vector search]. Defaults to [0.5, 0.5].
    :param k: Number of top relevant chunks to retrieve.
    """
    # 1. Dense vector similarity retriever
    vector_retriever = vector_store.as_retriever(
        search_type='similarity',
        search_kwargs={"k": k}
    )

    # 2. Extract documents if not explicitly provided
    if docs is None:
        docs = get_documents_from_vector_store(vector_store)

    # Fallback to vector retriever if vector store is empty / has no docs
    if not docs:
        print("[!] Warning: No documents found for BM25 indexing. Returning vector retriever only.")
        return vector_retriever

    # 3. BM25 keyword retriever
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = k

    # 4. Hybrid Ensemble Retriever combining BM25 and Vector Search via Reciprocal Rank Fusion
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=weights
    )
    return ensemble_retriever


