import streamlit as st
import os
from pathlib import Path
from pdf_processor import PDFProcessor
from vector_store import VectorStore
from qa_chain import QAChain
from dotenv import load_dotenv
import tempfile
from PIL import Image
import plotly.express as px
import pandas as pd

# Load environment variables
load_dotenv()

# Initialize session state
if 'qa_chain' not in st.session_state:
    st.session_state.qa_chain = None
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'processed_file' not in st.session_state:
    st.session_state.processed_file = None
if 'visual_elements' not in st.session_state:
    st.session_state.visual_elements = None

def process_pdf(uploaded_file):
    """Process the uploaded PDF file."""
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    # Process the PDF
    processor = PDFProcessor(tmp_path)
    text_chunks, tables = processor.extract_text_and_tables()
    visual_elements = processor.get_visual_elements()
    
    # Initialize vector store
    vector_store = VectorStore()
    vector_store.create_collection(name="annual_report")
    
    # Add documents to vector store
    vector_store.add_documents(text_chunks, metadata={'source': uploaded_file.name})
    
    # Add visual elements to vector store with their analysis
    visual_docs = []
    for element in visual_elements:
        if element['type'] == 'chart':
            visual_docs.append({
                'content': element['analysis'],
                'page': element['page'],
                'type': 'chart_analysis'
            })
    vector_store.add_documents(visual_docs, metadata={'source': uploaded_file.name})
    
    # Initialize QA chain
    qa_chain = QAChain(vector_store)
    
    # Update session state
    st.session_state.qa_chain = qa_chain
    st.session_state.vector_store = vector_store
    st.session_state.processed_file = uploaded_file.name
    st.session_state.visual_elements = visual_elements
    
    # Clean up
    os.unlink(tmp_path)
    processor.cleanup()
    
    return processor.get_metadata()

def display_visual_element(element):
    """Display a visual element with its analysis."""
    try:
        image = Image.open(element['image_path'])
        st.image(image, use_column_width=True)
        
        if element['type'] == 'chart':
            st.markdown("### Chart Analysis")
            st.markdown(element['analysis'])
        elif element['type'] == 'table':
            st.markdown("### Table Content")
            st.markdown(f"```\n{element['content']}\n```")
    except Exception as e:
        st.error(f"Error displaying visual element: {str(e)}")

# Streamlit UI
st.set_page_config(
    page_title="Annual Report Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Annual Report Analyzer")
st.markdown("""
This application helps you analyze annual reports using AI. Upload a PDF of an annual report
and ask questions about its contents in natural language. The system can analyze text, tables,
charts, and other visual elements.
""")

# File upload
uploaded_file = st.file_uploader("Upload Annual Report (PDF)", type="pdf")

if uploaded_file:
    if st.session_state.processed_file != uploaded_file.name:
        with st.spinner("Processing the annual report... This may take a few minutes."):
            metadata = process_pdf(uploaded_file)
            st.success(f"Successfully processed {metadata['total_pages']} pages!")

    # Create tabs for different views
    tab1, tab2 = st.tabs(["💬 Q&A", "📈 Visual Elements"])
    
    with tab1:
        # Display chat interface
        st.markdown("### Ask Questions")
        question = st.text_input("What would you like to know about the annual report?")
        
        if question:
            if st.session_state.qa_chain is None:
                st.error("Please wait for the document to finish processing.")
            else:
                with st.spinner("Analyzing..."):
                    response = st.session_state.qa_chain.ask(question)
                    
                    # Display answer
                    st.markdown("#### Answer:")
                    st.markdown(response['answer'])
                    
                    # Display sources
                    with st.expander("View Sources"):
                        for idx, source in enumerate(response['source_documents'], 1):
                            st.markdown(f"**Source {idx}** (Page {source['metadata'].get('page', 'Unknown')})")
                            st.markdown(source['content'])
                            st.markdown("---")

        # Display chat history
        if st.session_state.qa_chain is not None:
            with st.expander("View Chat History"):
                history = st.session_state.qa_chain._format_chat_history()
                for message in history:
                    role = "🤖 AI" if message['role'] == 'assistant' else "👤 You"
                    st.markdown(f"**{role}:** {message['content']}")
                    st.markdown("---")
    
    with tab2:
        # Display visual elements
        if st.session_state.visual_elements:
            st.markdown("### Visual Elements from the Report")
            
            # Group elements by page
            elements_by_page = {}
            for element in st.session_state.visual_elements:
                page = element['page']
                if page not in elements_by_page:
                    elements_by_page[page] = []
                elements_by_page[page].append(element)
            
            # Display elements page by page
            for page in sorted(elements_by_page.keys()):
                with st.expander(f"Page {page}"):
                    elements = elements_by_page[page]
                    
                    # Create columns for visual elements
                    cols = st.columns(min(len(elements), 2))
                    for idx, element in enumerate(elements):
                        with cols[idx % 2]:
                            display_visual_element(element)

else:
    st.info("Please upload an annual report to begin analysis.") 