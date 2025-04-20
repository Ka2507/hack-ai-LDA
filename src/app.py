import streamlit as st
import requests
import os
from typing import List, Dict, Any
import tempfile

# Initialize session state variables
if 'vector_stores' not in st.session_state:
    st.session_state.vector_stores = []
if 'qa_chain' not in st.session_state:
    st.session_state.qa_chain = None
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'sources' not in st.session_state:
    st.session_state.sources = []
if 'current_conversation' not in st.session_state:
    st.session_state.current_conversation = []
if 'max_reports' not in st.session_state:
    st.session_state.max_reports = 3

def process_pdf(file):
    """Process a PDF file and update the QA chain."""
    try:
        # Create a temporary file to store the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = file.getvalue()
            temp_file.write(content)
            temp_file.flush()
            
            # Send file to backend
            files = {"file": (file.name, content, "application/pdf")}
            response = requests.post("http://localhost:8501/api/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.processed_files.append(file.name)
                st.success(f"File processed successfully! ({len(st.session_state.processed_files)}/{st.session_state.max_reports} reports)")
                return True
            else:
                st.error(f"Error processing file: {response.json().get('detail', 'Unknown error')}")
                return False
                
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return False
    finally:
        if 'temp_file' in locals():
            os.unlink(temp_file.name)

def reset_reports():
    """Reset all reports and conversation history."""
    try:
        response = requests.post("http://localhost:8501/api/reset")
        if response.status_code == 200:
            st.session_state.vector_stores = []
            st.session_state.qa_chain = None
            st.session_state.processed_files = []
            st.session_state.chat_history = []
            st.session_state.sources = []
            st.session_state.current_conversation = []
            st.success("Reports reset successfully!")
        else:
            st.error(f"Error resetting reports: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error resetting reports: {str(e)}")

# Streamlit UI
st.title("Annual Report Analyzer")

# File Upload Section
st.header("Upload Reports")
uploaded_files = st.file_uploader("Upload PDF files (up to 3)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.processed_files and len(st.session_state.processed_files) < st.session_state.max_reports:
            process_pdf(file)

# Reset Button
if st.button("Reset All Reports"):
    reset_reports()

# Q&A Section
st.header("Ask Questions")
if st.session_state.processed_files:
    st.subheader("Current Reports")
    for i, file in enumerate(st.session_state.processed_files, 1):
        st.write(f"{i}. {file}")
    
    # Create tabs for Q&A, Sources, and Chat History
    qa_tab, sources_tab, history_tab = st.tabs(["Q&A", "Sources", "Chat History"])
    
    with qa_tab:
        st.subheader("Current Conversation")
        for exchange in st.session_state.current_conversation:
            st.write(f"Q: {exchange['question']}")
            st.write(f"A: {exchange['answer']}")
            st.write("---")
        
        question = st.text_input("Enter your question:")
        if question:
            try:
                is_follow_up = len(st.session_state.current_conversation) > 0
                response = requests.post(
                    "http://localhost:8501/api/question",
                    json={"question": question, "is_follow_up": is_follow_up}
                )
                
                if response.status_code == 200:
                    answer = response.json()["answer"]
                    st.session_state.current_conversation.append({
                        "question": question,
                        "answer": answer
                    })
                    st.session_state.chat_history.append({
                        "question": question,
                        "answer": answer
                    })
                    st.write("Answer:", answer)
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
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
    st.info("Please upload at least one PDF file to start asking questions.") 