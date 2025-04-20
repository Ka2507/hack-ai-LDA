from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from typing import Dict, Any
from src.vector_store import VectorStore
from src.qa_chain import QAChain

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
vector_store = None
qa_chain = None

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    global vector_store, qa_chain
    
    try:
        # Create a temporary file to store the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Initialize VectorStore and process the PDF
            vector_store = VectorStore()
            vector_store.create_collection()
            
            # Add documents to vector store
            vector_store.add_documents([{
                "content": content.decode('utf-8', errors='ignore'),
                "metadata": {"source": file.filename}
            }])
            
            # Initialize QA chain
            qa_chain = QAChain(vector_store)
            
            # Clean up the temporary file
            os.unlink(temp_file.name)
            
            return {"message": "File uploaded and processed successfully"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/question")
async def ask_question(request: Dict[str, Any]):
    global qa_chain
    
    if not qa_chain:
        raise HTTPException(status_code=400, detail="Please upload a PDF file first")
        
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
    uvicorn.run(app, host="0.0.0.0", port=8000)