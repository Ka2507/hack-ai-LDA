from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate # No longer needed directly here
from langchain.chains import RetrievalQA # Import RetrievalQA chain
from langchain.prompts import PromptTemplate # Import standard PromptTemplate
from dotenv import load_dotenv
from typing import List, Dict, Any
# import tiktoken # No longer needed directly here

# Load environment variables
load_dotenv()

# --- Define the Prompt Template --- 
# Moved outside the class for clarity
prompt_template = """You are an expert financial analyst assistant. Your task is to analyze and extract insights from the provided annual report context ONLY.
Strictly use the provided "Context from Reports" to answer the question. DO NOT use external knowledge or make up information.
If the answer cannot be found in the provided context, state clearly "The answer is not available in the provided document context."

When answering:
-   Identify key financial metrics, strategic initiatives, risks, and market positioning mentioned in the context.
-   Explain the *business significance* of the findings based *only* on the information presented in the reports.
-   Use bullet points for clarity where appropriate (e.g., listing key findings, risks, or comparisons).
-   If the question involves comparison between reports (if multiple contexts are provided), focus on:
    1.  Key quantitative differences (e.g., revenue growth, profit margin changes).
    2.  Key qualitative differences (e.g., changes in strategy, reported risks, market outlook).
    3.  Summarize the main insights derived *directly* from comparing the provided texts.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""
QA_PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)
# --------------------------------

class QAChain:
    def __init__(self, vector_stores: List[Any]):
        """Initialize the QA chain with multiple vector stores."""
        # NOTE: Using only the *first* vector store for simplicity with RetrievalQA
        # A more complex setup could combine retrievers if needed.
        if not vector_stores:
            raise ValueError("At least one vector store must be provided.")
        self.vector_store = vector_stores[0] # Use the first store
        # self.conversation_history: List[Dict[str, str]] = [] # History managed by caller now
        
        # Initialize the language model
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.1, # Lower temperature for more factual answers
            max_tokens=1000
        )
        
        # --- Create RetrievalQA Chain --- 
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff", # Uses all retrieved docs in context
            retriever=self.vector_store.get_retriever(search_kwargs={"k": 4}), # Retrieve top 4 chunks
            return_source_documents=True, # <<< Key change to return sources
            chain_type_kwargs={"prompt": QA_PROMPT}
        )
        # ------------------------------

    # Removed _get_context, _format_history, _count_tokens as RetrievalQA handles retrieval and prompting

    def run(self, question: str) -> Dict[str, Any]: # Modified to return dict
        """
        Ask a question using the RetrievalQA chain.
        
        Args:
            question: The question to ask
            
        Returns:
            A dictionary containing the 'answer' and 'source_documents'
        """
        try:
            # Invoke the RetrievalQA chain
            # It handles retrieving context based on the question and formatting the prompt
            result = self.qa_chain.invoke({"query": question})
            
            # Prepare the output dictionary
            output = {
                "answer": result.get("result", "Error: Could not parse answer from chain."),
                "source_documents": result.get("source_documents", [])
            }
            return output
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error in QAChain run method: {error_msg}")
            # Return error information in the expected dictionary format
            return {
                 "answer": f"I apologize, but I encountered an error: {error_msg}",
                 "source_documents": []
            } 