from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from typing import Dict, Any, List
from vector_store import VectorStore
from qa_chain import QAChain
from pypdf import PdfReader

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
                for page in reader.pages:
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
            
            # Initialize VectorStore and process the PDF
            vector_store = VectorStore()
            vector_store.create_collection()
            
            # Add *extracted* text to vector store
            # Consider splitting the text_content into smaller chunks here for better retrieval
            # For simplicity, adding the whole text for now
            vector_store.add_texts([text_content], [{"source": file.filename}])
            
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
    vector_stores = []
    qa_chain = None
    return {"message": "Reports reset successfully"}

@app.post("/api/question")
async def ask_question(request: Dict[str, Any]):
    global qa_chain
    
    if not qa_chain or not vector_stores:
        raise HTTPException(status_code=400, detail="Please upload at least one PDF file first")
        
    try:
        question = request.get("question")
        is_follow_up = request.get("is_follow_up", False)
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
            
        result = qa_chain.run(question, is_follow_up)
        # Extract just the answer string from the result
        if isinstance(result, dict):
            answer = result.get('answer', str(result))
        else:
            answer = str(result)
            
        return {"answer": answer}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
