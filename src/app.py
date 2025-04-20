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
if 'chat_history' not in st.session_state: # Combined history for both modes
    st.session_state.chat_history = []
if 'sources' not in st.session_state: # Sources only relevant for RAG mode
    st.session_state.sources = []
if 'last_rag_sources' not in st.session_state: # Store sources for the last RAG Q
    st.session_state.last_rag_sources = []
if 'max_reports' not in st.session_state:
    st.session_state.max_reports = 3
if 'chat_mode' not in st.session_state: # Add state for chat mode
    st.session_state.chat_mode = "Analyze Reports"

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
        response = requests.post("http://localhost:8501/api/reset") # Resets backend RAG state
        if response.status_code == 200:
            st.session_state.vector_stores = []
            st.session_state.qa_chain = None
            st.session_state.processed_files = []
            st.session_state.chat_history = [] # Clear frontend history too
            st.session_state.sources = []
            st.session_state.last_rag_sources = [] # Clear sources on reset
            st.success("Reports and chat history reset successfully!")
            st.rerun() # Rerun to clear UI elements
        else:
            st.error(f"Error resetting reports: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error resetting reports: {str(e)}")

# Streamlit UI
st.title("Annual Report Analyzer & Chatbot")

# --- Chat Mode Selection --- 
st.radio(
    "Select Mode:",
    ["Analyze Reports", "General Chat"],
    key='chat_mode',
    horizontal=True,
)
st.info(f"Current Mode: **{st.session_state.chat_mode}**")
# --------------------------

# File Upload Section - Only show if in Analyze Reports mode
st.header("Manage Reports") # Renamed header
if st.session_state.chat_mode == "Analyze Reports":
    uploaded_files = st.file_uploader("Upload PDF files (up to 3)", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            if file.name not in st.session_state.processed_files and len(st.session_state.processed_files) < st.session_state.max_reports:
                process_pdf(file)
    
    # Display current reports 
    if st.session_state.processed_files:
        st.subheader("Current Reports for Analysis")
        for i, file in enumerate(st.session_state.processed_files, 1):
            st.write(f"{i}. {file}")
    else:
        st.write("No reports uploaded yet.")

    # Reset Button
    if st.button("Reset All Reports & Chat History"):
        reset_reports()
else:
    st.info("Switch to 'Analyze Reports' mode to upload and query PDFs.")


# Q&A Section
st.header("Ask Questions")

# Create tabs (Sources tab is conditional)
tabs_list = ["Q&A", "Chat History"]
if st.session_state.chat_mode == "Analyze Reports":
    tabs_list.insert(1, "Sources") 
active_tabs = st.tabs(tabs_list)

# --- Q&A Tab --- 
with active_tabs[0]: 
    st.subheader("Current Conversation")
    # Display chat history (unified for both modes)
    for exchange in st.session_state.chat_history:
        st.write(f"**Q:** {exchange['question']}")
        st.write(f"**A:** {exchange['answer']}")
        # --- Add Hallucination Warning (Implementation Step 3) --- 
        uncertainty_phrases = [
            "not available in the provided document context",
            "do not have information",
            "cannot find details",
            "based on the provided context",
            "insufficient information"
        ]
        if any(phrase in exchange['answer'].lower() for phrase in uncertainty_phrases):
            st.warning("⚠️ The answer indicates it might be based on limited information found in the document.")
        # --------------------------------------------------------
        st.write("---")

    # --- Use st.form for input and submission --- 
    with st.form(key='qa_form'):
        question_input = st.text_input(
            "Enter your question:", 
            key="qa_input_field", # Use a distinct key for the widget itself
            placeholder=f"Ask in {st.session_state.chat_mode} mode..."
        )
        submitted = st.form_submit_button("Ask")

        if submitted:
            # Retrieve the actual question from the input field state
            question = question_input 
            
            if not question.strip(): # Check if input is empty or just whitespace
                st.warning("Please enter a question.")
            else:
                # --- Logic moved inside form submission check --- 
                api_url = None
                payload = None
                proceed = True

                if st.session_state.chat_mode == "Analyze Reports":
                    if not st.session_state.processed_files:
                        st.warning("Please upload at least one PDF file in 'Analyze Reports' mode before asking questions.")
                        proceed = False
                    else:
                        api_url = "http://localhost:8501/api/question"
                        payload = {"question": question}
                else: # General Chat mode
                    api_url = "http://localhost:8501/api/general_chat"
                    payload = {"question": question}

                if proceed and api_url and payload:
                    try:
                        response = requests.post(api_url, json=payload)
                        if response.status_code == 200:
                            response_data = response.json()
                            answer = response_data.get("answer", "Error: Could not parse answer.")
                            st.session_state.chat_history.append({"question": question, "answer": answer})
                            if st.session_state.chat_mode == "Analyze Reports":
                                st.session_state.last_rag_sources = response_data.get("sources", [])
                            else:
                                st.session_state.last_rag_sources = [] 
                            # Form submission handles rerun, no explicit call needed
                        else:
                            st.error(f"Error from API: {response.json().get('detail', 'Unknown error')} (Status code: {response.status_code})")
                    except requests.exceptions.RequestException as e:
                         st.error(f"Connection error: Failed to connect to the backend API. Is it running? ({e})")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")
                # --- End of logic moved inside form --- 

# --- Sources Tab (Conditional & Updated) --- 
if st.session_state.chat_mode == "Analyze Reports":
    with active_tabs[1]: 
        st.subheader("Sources for Last Question")
        if st.session_state.last_rag_sources:
            for i, source in enumerate(st.session_state.last_rag_sources):
                try:
                    # Extract metadata safely with defaults
                    metadata = source.get("metadata", {})
                    source_file = metadata.get("source", "Unknown File")
                    chunk_num = metadata.get("chunk", "N/A")
                    page_content = source.get("page_content", "N/A")
                    
                    # Display source info
                    with st.expander(f"Source Chunk {i+1} (from {source_file}, chunk {chunk_num})", expanded=False):
                        st.text(page_content)
                except Exception as display_error:
                    st.error(f"Error displaying source {i+1}: {display_error}")
        else:
            st.info("Ask a question in 'Analyze Reports' mode to see the sources used for the answer here.")

# --- Chat History Tab --- 
history_tab_index = 2 if st.session_state.chat_mode == "Analyze Reports" else 1
with active_tabs[history_tab_index]:
    st.subheader("Full Chat History")
    if st.session_state.chat_history:
        for i, chat in enumerate(reversed(st.session_state.chat_history)): # Show newest first
             with st.expander(f"Q: {chat['question']}", expanded=(i==0)): # Expand newest
                 st.write("A:", chat['answer'])
        if st.button("Clear Displayed Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    else:
        st.info("Chat history is empty.")

# Show initial info message 
if not st.session_state.processed_files and st.session_state.chat_mode == "Analyze Reports" and not st.session_state.chat_history:
    st.info("Upload PDFs above to start analyzing reports.")
elif st.session_state.chat_mode == "General Chat" and not st.session_state.chat_history:
    st.info("You are in General Chat mode. Ask any question.")
# -------------------------------------------- 