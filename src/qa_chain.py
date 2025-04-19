from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class QAChain:
    def __init__(self, vector_store):
        """Initialize the QA chain with a vector store."""
        self.vector_store = vector_store
        self.chat_history = []
        
        # Initialize the language model
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7
        )
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial analyst assistant specialized in analyzing annual reports.
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            Use bullet points and formatting to make your answers clear and readable when appropriate."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Context: {context}\n\nQuestion: {question}")
        ])

    def _get_context(self, question: str) -> str:
        """Get relevant context for the question."""
        try:
            docs = self.vector_store.get_retriever().get_relevant_documents(question)
            return self._format_docs(docs)
        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return ""

    def _format_docs(self, docs):
        """Format documents into a string."""
        try:
            return "\n\n".join(str(doc.page_content) for doc in docs)
        except Exception as e:
            print(f"Error formatting docs: {str(e)}")
            return ""

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Ask a question about the annual report.
        
        Args:
            question: The question to ask
            
        Returns:
            Dictionary containing the answer and relevant metadata
        """
        try:
            # Get the context first
            context = self._get_context(question)
            
            # Create the chain for this specific question
            chain = self.prompt | self.llm
            
            # Get the answer
            response = chain.invoke({
                "context": context,
                "question": question,
                "chat_history": self.chat_history
            })
            
            # Update chat history
            self.chat_history.extend([
                HumanMessage(content=question),
                AIMessage(content=response.content)
            ])
            
            # Get the relevant documents for the response
            docs = self.vector_store.get_retriever().get_relevant_documents(question)
            
            # Format the response
            result = {
                'answer': response.content,
                'source_documents': self._format_source_documents(docs),
                'chat_history': self._format_chat_history()
            }
            
            return result
        except Exception as e:
            print(f"Error in ask method: {str(e)}")
            return {
                'answer': "I apologize, but I encountered an error while processing your question. Please try again.",
                'source_documents': [],
                'chat_history': self._format_chat_history()
            }

    def _format_source_documents(self, docs: List[Any]) -> List[Dict[str, Any]]:
        """Format source documents for the response."""
        try:
            formatted_docs = []
            for doc in docs:
                formatted_docs.append({
                    'content': str(doc.page_content),
                    'metadata': doc.metadata
                })
            return formatted_docs
        except Exception as e:
            print(f"Error formatting source documents: {str(e)}")
            return []

    def _format_chat_history(self) -> List[Dict[str, str]]:
        """Format chat history for the response."""
        try:
            history = []
            for i in range(0, len(self.chat_history), 2):
                if i + 1 < len(self.chat_history):
                    history.append({
                        'role': 'human',
                        'content': str(self.chat_history[i].content)
                    })
                    history.append({
                        'role': 'assistant',
                        'content': str(self.chat_history[i + 1].content)
                    })
            return history
        except Exception as e:
            print(f"Error formatting chat history: {str(e)}")
            return []

    def clear_memory(self):
        """Clear the conversation memory."""
        self.chat_history = [] 