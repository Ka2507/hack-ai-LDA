import os
from typing import List, Dict, Any
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

class VectorStore:
    def __init__(self, persist_directory: str = "data/chroma"):
        """Initialize the vector store with a persistence directory."""
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None

    def create_collection(self, name: str = "annual_report"):
        """Create or get a collection for storing document embeddings."""
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=name
        )
        return self.vectorstore

    def add_texts(self, texts: list[str], metadatas: list[dict] = None):
        """Add texts to the vector store."""
        if self.vectorstore is None:
            self.create_collection()
        
        if metadatas is None:
            metadatas = [{"page": i} for i in range(len(texts))]
            
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas)

    def get_retriever(self, search_kwargs=None):
        """Get a retriever for question answering."""
        if self.vectorstore is None:
            raise ValueError("No collection initialized. Call create_collection first.")
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs or {"k": 5})

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents."""
        if self.vectorstore is None:
            raise ValueError("No collection initialized. Call create_collection first.")

        docs = self.vectorstore.similarity_search_with_relevance_scores(query, k=n_results)
        
        formatted_results = []
        for doc, score in docs:
            formatted_results.append({
                'content': doc.page_content,
                'metadata': doc.metadata,
                'relevance_score': score
            })

        return formatted_results

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        if self.vectorstore is None:
            return {'status': 'No collection initialized'}
        
        return {
            'total_documents': len(self.vectorstore.get()["ids"]),
            'name': self.vectorstore._collection.name
        }

    def persist(self):
        """Ensure all data is persisted to disk."""
        if self.vectorstore is not None:
            self.vectorstore.persist()
        
    def reset(self):
        """Reset the vector store."""
        if self.vectorstore is not None:
            self.vectorstore = None 