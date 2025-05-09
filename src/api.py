from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil # Import shutil for directory removal
from typing import Dict, Any, List
from vector_store import VectorStore
from qa_chain import QAChain
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter # Added text splitter

# Load environment variables (needed for general chat key too)
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to maintain state
vector_stores: List[VectorStore] = []
qa_chain = None
MAX_REPORTS = 3

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    global vector_stores, qa_chain
    
    try:
        # --- Safeguard Reset for First Upload --- 
        if not vector_stores: # If this is the first file after a potential reset
            persist_dir = "data/chroma" 
            if os.path.exists(persist_dir):
                try:
                    print(f"First upload detected, ensuring {persist_dir} is cleared.")
                    shutil.rmtree(persist_dir)
                except Exception as e:
                    print(f"Error clearing {persist_dir} before first upload: {e}")
                    raise HTTPException(status_code=500, detail="Failed to clear old storage before upload.")
        # --------------------------------------

        if len(vector_stores) >= MAX_REPORTS:
            raise HTTPException(status_code=400, detail=f"Maximum number of reports ({MAX_REPORTS}) reached")
            
        # Create a temporary file to store the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Correct PDF Text Extraction
            text_content = ""
            try:
                reader = PdfReader(temp_file.name)
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:  # Ensure text was extracted
                        text_content += page_text + "\n"  # Add text and newline
            except Exception as pdf_error:
                # Clean up temp file even if PDF processing fails
                os.unlink(temp_file.name)
                raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {pdf_error}")
            # -------------------------------------

            if not text_content:  # Check if any text was extracted
                os.unlink(temp_file.name)
                raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")
            
            # Text Splitting
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, # Adjust size as needed
                chunk_overlap=200, # Adjust overlap as needed
                length_function=len,
            )
            chunks = text_splitter.split_text(text_content)
            if not chunks:
                os.unlink(temp_file.name)
                raise HTTPException(status_code=400, detail="Failed to split extracted text into chunks.")
            print(f"Split PDF into {len(chunks)} chunks.") # Log chunk count
            # ----------------------
            
            # Initialize VectorStore and process the PDF
            vector_store = VectorStore()
            vector_store.create_collection()
            
            # Add *extracted* text to vector store
            metadatas = [{"source": file.filename, "chunk": i} for i in range(len(chunks))]
            vector_store.add_texts(texts=chunks, metadatas=metadatas)
            
            # Add to vector stores list
            vector_stores.append(vector_store)
            
            # Initialize or update QA chain
            qa_chain = QAChain(vector_stores)
            
            # Clean up the temporary file
            os.unlink(temp_file.name)
            
            return {
                "message": "File uploaded and processed successfully",
                "current_reports": len(vector_stores),
                "max_reports": MAX_REPORTS
            }
            
    except Exception as e:
        # Catch potential HTTPExceptions raised earlier
        if isinstance(e, HTTPException):
            raise e 
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def reset_reports():
    global vector_stores, qa_chain
    
    # Reset in-memory state
    vector_stores = []
    qa_chain = None
    
    # --- Delete persistent ChromaDB data --- 
    persist_dir = "data/chroma" # Assuming default from VectorStore
    if os.path.exists(persist_dir):
        try:
            shutil.rmtree(persist_dir)
            print(f"Successfully deleted persistent storage: {persist_dir}")
        except Exception as e:
            print(f"Error deleting persistent storage {persist_dir}: {e}")
            # Decide if this should be a user-facing error or just logged
            # raise HTTPException(status_code=500, detail="Failed to fully reset storage.")
    # --------------------------------------
    
    return {"message": "Reports reset successfully"}

@app.post("/api/question")
async def ask_question(request: Dict[str, Any]):
    global qa_chain
    
    if not qa_chain or not vector_stores:
        raise HTTPException(status_code=400, detail="Please upload at least one PDF file first")
        
    try:
        question = request.get("question")
        # is_follow_up is no longer used by the refactored QAChain
        # is_follow_up = request.get("is_follow_up", False) 
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
            
        # Call the refactored run method which returns a dict
        result_dict = qa_chain.run(question)

        # --- Serialize Source Documents --- 
        # Convert LangChain Document objects to serializable dicts
        sources_serializable = []
        if result_dict.get("source_documents"):
            for doc in result_dict["source_documents"]:
                sources_serializable.append({
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                })
        # ---------------------------------
            
        # Return answer and serialized sources
        return {
            "answer": result_dict.get("answer", "Error: Missing answer"), 
            "sources": sources_serializable
            }
        
    except Exception as e:
        # Catch potential errors during chain execution
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# --- New Endpoint for General Chat --- 
@app.post("/api/general_chat")
async def general_chat(request: Dict[str, Any]):
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
            
        # Initialize a separate LLM client for general chat
        # (Could potentially reuse/refactor later)
        general_llm = ChatOpenAI(
            model_name="gpt-3.5-turbo", 
            temperature=0.7, 
            max_tokens=1000
        )
        
        # Simple invocation with just the human question
        # No RAG context or specific system prompt is used here
        response = general_llm.invoke([HumanMessage(content=question)])
        
        return {"answer": response.content}
        
    except Exception as e:
        # Handle potential OpenAI errors (like rate limits) gracefully
        error_msg = str(e)
        if "rate_limit_exceeded" in error_msg:
             raise HTTPException(status_code=429, detail="General chat limit reached. Please try again later.")
        raise HTTPException(status_code=500, detail=f"Error in general chat: {error_msg}")
# ------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
