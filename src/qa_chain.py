from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from typing import List, Dict, Any
import tiktoken

# Load environment variables
load_dotenv()

class QAChain:
    def __init__(self, vector_stores: List[Any]):
        """Initialize the QA chain with multiple vector stores."""
        self.vector_stores = vector_stores
        self.conversation_history: List[Dict[str, str]] = []
        
        # Initialize the language model
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1000  # Limit response length
        )
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial analyst assistant specialized in analyzing and comparing annual reports.
            Use the following pieces of context from multiple reports to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            Use bullet points and formatting to make your answers clear and readable when appropriate.
            For follow-up questions, use the conversation history to maintain context and provide more detailed answers.
            When comparing reports, highlight similarities and differences clearly.
            If the question is about comparing reports, structure your answer to show:
            1. Similarities between the reports
            2. Differences between the reports
            3. Key insights from the comparison"""),
            ("human", "Context from Reports:\n{context}\n\nConversation History: {history}\n\nQuestion: {question}")
        ])

    def _get_context(self, question: str) -> str:
        """Get relevant context from all reports for the question."""
        try:
            all_contexts = []
            for i, vector_store in enumerate(self.vector_stores, 1):
                docs = vector_store.get_retriever().get_relevant_documents(question)
                # Limit the number of documents to reduce token usage
                docs = docs[:3]  # Only use top 3 most relevant documents
                report_context = "\n\n".join(str(doc.page_content) for doc in docs)
                if report_context:
                    all_contexts.append(f"Report {i}:\n{report_context}")
            return "\n\n---\n\n".join(all_contexts)
        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return ""

    def _format_history(self) -> str:
        """Format the conversation history for the prompt."""
        if not self.conversation_history:
            return "No previous conversation."
        
        # Only keep the last 3 exchanges to limit token usage
        recent_history = self.conversation_history[-3:]
        formatted_history = []
        for i, exchange in enumerate(recent_history, 1):
            formatted_history.append(f"Q{i}: {exchange['question']}")
            formatted_history.append(f"A{i}: {exchange['answer']}")
        
        return "\n".join(formatted_history)

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(encoding.encode(text))

    def run(self, question: str, is_follow_up: bool = False) -> str:
        """
        Ask a question about the annual reports.
        
        Args:
            question: The question to ask
            is_follow_up: Whether this is a follow-up question
            
        Returns:
            The answer as a string
        """
        try:
            # Get the context from all reports
            context = self._get_context(question)
            
            # Format the conversation history
            history = self._format_history()
            
            # Check token count and limit if necessary
            total_tokens = self._count_tokens(context) + self._count_tokens(history) + self._count_tokens(question)
            if total_tokens > 15000:  # Limit total tokens to avoid rate limits
                context = context[:10000]  # Truncate context if too long
            
            # Create the chain for this specific question
            chain = self.prompt | self.llm
            
            # Get the answer
            response = chain.invoke({
                "context": context,
                "history": history,
                "question": question
            })
            
            # Store the question and answer in conversation history
            self.conversation_history.append({
                "question": question,
                "answer": response.content
            })
            
            return response.content
            
        except Exception as e:
            error_msg = str(e)
            if "rate_limit_exceeded" in error_msg:
                return "I apologize, but I'm currently experiencing high demand. Please try again in a few moments."
            elif "Request too large" in error_msg:
                return "I apologize, but the question requires processing too much information. Please try asking a more specific question or break it down into smaller parts."
            else:
                print(f"Error in run method: {error_msg}")
                return "I apologize, but I encountered an error while processing your question. Please try again." 