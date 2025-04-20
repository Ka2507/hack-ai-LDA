# Annual Report Analyzer

An AI-powered application that enables users to ask natural language questions about annual reports and receive meaningful answers. Built for the AIS HackAI 2025 LTIMindtree Hackathon Challenge.

## Features

- PDF annual report ingestion and processing
- Natural language question answering
- Intelligent information extraction from financial documents
- Interactive web interface
- Support for tables, charts, and text analysis

## Setup

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```
4. Run the application:
```bash
streamlit run src/app.py
```

## Project Structure

- `src/`: Source code directory
  - `app.py`: Main Streamlit application
  - `pdf_processor.py`: PDF processing utilities
  - `qa_chain.py`: Question-answering chain implementation
  - `vector_store.py`: Vector database management
- `data/`: Directory for storing processed documents
- `requirements.txt`: Project dependencies

## Usage

1. Launch the application
2. Upload an annual report PDF
3. Wait for the document to be processed
4. Ask questions in natural language about the report
5. Receive AI-generated answers based on the report's content

## Technologies Used

- LangChain for AI orchestration
- OpenAI for natural language processing
- ChromaDB for vector storage
- Streamlit for web interface
- PyPDF2 and pdfplumber for PDF processing
