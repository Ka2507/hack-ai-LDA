import streamlit as st
import fitz
from vector_store import VectorStore
from qa_chain import QAChain
import tempfile
import os
from pathlib import Path

# Initialize session state variables
if 'qa_chain' not in st.session_state:
    st.session_state.qa_chain = None
if 'processed_file' not in st.session_state:
    st.session_state.processed_file = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'sources' not in st.session_state:
    st.session_state.sources = []

def process_pdf(uploaded_file):
    try:
        # Create a temporary file to store the uploaded PDF
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / "temp.pdf"
        
        # Write the uploaded file to the temporary file
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        # Process the PDF and extract text
        doc = fitz.open(temp_path)
        text_content = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text_content.append(text)
        
        # Create vector store and QA chain
        vector_store = VectorStore()
        vector_store.add_texts(text_content)
        
        qa_chain = QAChain(vector_store)
        
        # Update session state
        st.session_state.qa_chain = qa_chain
        st.session_state.processed_file = uploaded_file.name
        
        # Clean up
        doc.close()
        os.unlink(temp_path)
        os.rmdir(temp_dir)
        
        return True
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        # Clean up in case of error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        return False

def main():
    st.title("PDF Document Analyzer")
    
    # File upload
    uploaded_file = st.file_uploader("Upload a PDF document", type=['pdf'])
    
    if uploaded_file:
        if st.session_state.processed_file != uploaded_file.name:
            with st.spinner("Processing document..."):
                success = process_pdf(uploaded_file)
                if not success:
                    st.error("Failed to process the document. Please try again.")
                    return
        
        # Create tabs for Q&A, Sources, and Chat History
        qa_tab, sources_tab, history_tab = st.tabs(["Q&A", "Sources", "Chat History"])
        
        with qa_tab:
            st.subheader("Ask Questions")
            question = st.text_input("Enter your question about the document:")
            
            if question and st.session_state.qa_chain:
                with st.spinner("Finding answer..."):
                    try:
                        # Get answer and context
                        answer = st.session_state.qa_chain.run(question)
                        context = st.session_state.qa_chain._get_context(question)
                        
                        # Update chat history
                        st.session_state.chat_history.append({
                            "question": question,
                            "answer": answer
                        })
                        
                        # Update sources
                        st.session_state.sources.append({
                            "question": question,
                            "context": context
                        })
                        
                        st.write("Answer:", answer)
                        
                    except Exception as e:
                        st.error(f"Error getting answer: {str(e)}")
        
        with sources_tab:
            st.subheader("Sources")
            if st.session_state.sources:
                for i, source in enumerate(st.session_state.sources):
                    with st.expander(f"Sources for: {source['question']}", expanded=False):
                        st.text(source['context'])
            else:
                st.info("No sources available yet. Ask a question to see the sources.")
        
        with history_tab:
            st.subheader("Chat History")
            if st.session_state.chat_history:
                for i, chat in enumerate(st.session_state.chat_history):
                    with st.expander(f"Q: {chat['question']}", expanded=False):
                        st.write("A:", chat['answer'])
            else:
                st.info("No chat history available yet. Start asking questions to build history.")
    else:
        st.info("Please upload a PDF document to begin analysis.")

if __name__ == "__main__":
    main() 