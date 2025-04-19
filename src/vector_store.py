import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import json
from pathlib import Path
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

class VectorStore:
    def __init__(self, persist_directory: str = "data/chroma"):
        """Initialize the vector store with a persistence directory."""
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None
        self.collection = None

    def create_collection(self, name: str = "annual_report"):
        """Create or get a collection for storing document embeddings."""
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=name
        )
        return self.vectorstore

    def add_documents(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document chunks with their content
            metadata: Additional metadata about the documents
        """
        if self.vectorstore is None:
            self.create_collection()

        # Prepare documents for insertion
        texts = []
        metadatas = []

        for doc in documents:
            texts.append(doc['content'])
            
            # Combine document-specific metadata with global metadata
            doc_metadata = {
                'page': doc.get('page', 0),
                'type': doc.get('type', 'text')
            }
            if metadata:
                doc_metadata.update(metadata)
            metadatas.append(doc_metadata)

        # Add documents to the collection
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas)

    def get_retriever(self, search_kwargs=None):
        """Get a LangChain compatible retriever."""
        if self.vectorstore is None:
            raise ValueError("No collection initialized. Call create_collection first.")
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs or {"k": 5})

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents based on a query.
        
        Args:
            query: The search query
            n_results: Number of results to return
            
        Returns:
            List of relevant documents with their metadata
        """
        if self.vectorstore is None:
            raise ValueError("No collection initialized. Call create_collection first.")

        docs = self.vectorstore.similarity_search_with_relevance_scores(query, k=n_results)
        
        # Format results
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