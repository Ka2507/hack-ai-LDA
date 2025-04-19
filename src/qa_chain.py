from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class QAChain:
    def __init__(self, vector_store):
        """Initialize the QA chain with a vector store."""
        self.vector_store = vector_store
        
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
            ("human", "Context: {context}\n\nQuestion: {question}")
        ])

    def _get_context(self, question: str) -> str:
        """Get relevant context for the question."""
        try:
            docs = self.vector_store.get_retriever().get_relevant_documents(question)
            return "\n\n".join(str(doc.page_content) for doc in docs)
        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return ""

    def run(self, question: str) -> str:
        """
        Ask a question about the annual report.
        
        Args:
            question: The question to ask
            
        Returns:
            The answer as a string
        """
        try:
            # Get the context first
            context = self._get_context(question)
            
            # Create the chain for this specific question
            chain = self.prompt | self.llm
            
            # Get the answer
            response = chain.invoke({
                "context": context,
                "question": question
            })
            
            return response.content
            
        except Exception as e:
            print(f"Error in run method: {str(e)}")
            return "I apologize, but I encountered an error while processing your question. Please try again." 