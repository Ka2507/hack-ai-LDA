import pdfplumber
import pandas as pd
from typing import List, Dict, Tuple
import os
from pathlib import Path
from pdf2image import convert_from_path
from multimodal_processor import MultiModalProcessor
import tempfile

class PDFProcessor:
    def __init__(self, pdf_path: str):
        """Initialize the PDF processor with a path to the PDF file."""
        self.pdf_path = pdf_path
        self.text_chunks = []
        self.tables = []
        self.visual_elements = []
        self.metadata = {}
        self.multimodal_processor = MultiModalProcessor()

    def extract_text_and_tables(self) -> Tuple[List[str], List[Dict]]:
        """
        Extract text and tables from the PDF document.
        Returns a tuple of (text_chunks, tables)
        """
        # Convert PDF to images for visual processing
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(self.pdf_path)
            
            # Process each page
            for page_num, image in enumerate(images, 1):
                # Process visual elements
                visual_elements = self.multimodal_processor.process_page(image, page_num)
                self.visual_elements.extend(visual_elements)

        # Process text and tables using pdfplumber
        with pdfplumber.open(self.pdf_path) as pdf:
            self.metadata = {
                'total_pages': len(pdf.pages),
                'document_info': pdf.metadata
            }
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                text = page.extract_text()
                if text:
                    # Split text into smaller chunks for better processing
                    chunks = self._split_text_into_chunks(text)
                    for chunk in chunks:
                        self.text_chunks.append({
                            'content': chunk,
                            'page': page_num,
                            'type': 'text'
                        })
                
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        self.tables.append({
                            'data': df.to_dict('records'),
                            'page': page_num,
                            'type': 'table'
                        })
        
        return self.text_chunks, self.tables

    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into smaller chunks for better processing."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def get_metadata(self) -> Dict:
        """Return metadata about the processed document."""
        return self.metadata

    def get_visual_elements(self) -> List[Dict]:
        """Return extracted visual elements."""
        return self.visual_elements

    def save_processed_data(self, output_dir: str) -> Dict[str, str]:
        """
        Save processed text, tables, and visual elements to files.
        Returns paths to saved files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save text chunks
        text_path = output_dir / 'processed_text.json'
        pd.DataFrame(self.text_chunks).to_json(text_path, orient='records')
        
        # Save tables
        tables_path = output_dir / 'extracted_tables.json'
        pd.DataFrame(self.tables).to_json(tables_path, orient='records')
        
        # Save visual elements
        visuals_path = output_dir / 'visual_elements.json'
        pd.DataFrame(self.visual_elements).to_json(visuals_path, orient='records')
        
        # Save metadata
        metadata_path = output_dir / 'metadata.json'
        pd.Series(self.metadata).to_json(metadata_path)
        
        return {
            'text': str(text_path),
            'tables': str(tables_path),
            'visuals': str(visuals_path),
            'metadata': str(metadata_path)
        }

    def cleanup(self):
        """Clean up temporary files and resources."""
        self.multimodal_processor.cleanup() 