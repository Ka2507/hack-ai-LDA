import cv2
import numpy as np
import PyPDF2
from io import BytesIO
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import base64
import io
from typing import List, Dict, Any, Tuple, Union
import os
import json
from pathlib import Path
import tempfile
import openai
from dotenv import load_dotenv

load_dotenv()

class MultiModalProcessor:
    def __init__(self, pdf_file):
        """Initialize the processor with a PDF file."""
        self.pdf_file = pdf_file
        # Convert UploadedFile to bytes for PyPDF2
        if hasattr(pdf_file, 'read'):
            pdf_bytes = BytesIO(pdf_file.read())
            self.pdf_reader = PyPDF2.PdfReader(pdf_bytes)
            # Reset file pointer for future reads
            pdf_file.seek(0)
        else:
            # Handle case where pdf_file is already bytes or a file path
            self.pdf_reader = PyPDF2.PdfReader(pdf_file)
            
        self.min_table_area = 5000  # Minimum area for table detection
        self.min_figure_area = 3000  # Minimum area for figure detection
        self.temp_files = []

    def process_page(self, image: Union[Image.Image, bytes, np.ndarray], page_num: int) -> Dict[str, Any]:
        """
        Process a single page image and extract visual elements.
        
        Args:
            image: PIL Image object, bytes, or numpy array of the page
            page_num: Page number for reference
            
        Returns:
            Dictionary containing detected elements
        """
        # Convert input to OpenCV format
        if isinstance(image, bytes):
            # Convert bytes to numpy array
            nparr = np.frombuffer(image, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image, Image.Image):
            # Convert PIL Image to numpy array
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        elif isinstance(image, np.ndarray):
            # If already numpy array, ensure it's in BGR format
            if len(image.shape) == 2:  # Grayscale
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif image.shape[2] == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            elif image.shape[2] == 3 and image.dtype == np.uint8:
                pass  # Already in correct format
            else:
                raise ValueError("Unsupported image format")
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect tables using contours
        table_regions = self._detect_tables(gray)
        
        # Detect figures using edge detection
        figure_regions = self._detect_figures(gray)
        
        return {
            'tables': table_regions,
            'figures': figure_regions
        }

    def _detect_tables(self, gray_image: np.ndarray) -> List[Dict[str, int]]:
        """Detect table regions using contour detection."""
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray_image, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours to identify potential tables
        table_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_table_area:
                x, y, w, h = cv2.boundingRect(contour)
                # Check if the shape is roughly rectangular
                if 0.5 < w/h < 2.0:
                    table_regions.append({'x': x, 'y': y, 'width': w, 'height': h})
        
        return table_regions

    def _detect_figures(self, gray_image: np.ndarray) -> List[Dict[str, int]]:
        """Detect figure regions using edge detection."""
        # Apply Canny edge detection
        edges = cv2.Canny(gray_image, 100, 200)
        
        # Find contours in the edge image
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours to identify potential figures
        figure_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_figure_area:
                x, y, w, h = cv2.boundingRect(contour)
                # Check if the shape has a reasonable aspect ratio
                if 0.2 < w/h < 5.0:
                    figure_regions.append({'x': x, 'y': y, 'width': w, 'height': h})
        
        return figure_regions

    def cleanup(self):
        """Clean up any temporary files."""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file) 