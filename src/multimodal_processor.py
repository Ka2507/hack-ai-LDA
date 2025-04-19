import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import base64
import io
from typing import List, Dict, Any, Tuple
import os
import json
from pathlib import Path
import tempfile
import openai
from dotenv import load_dotenv

load_dotenv()

class MultiModalProcessor:
    def __init__(self, temp_dir: str = "temp_images"):
        """Initialize the multimodal processor."""
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_elements = []

    def process_page(self, page_image: Image.Image, page_num: int) -> List[Dict[str, Any]]:
        """Process a single page image to extract visual elements."""
        # Convert PIL Image to OpenCV format
        img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
        
        # Extract elements
        elements = []
        
        # Detect tables using contour detection
        tables = self._detect_tables(img_cv)
        elements.extend(self._process_tables(tables, page_num))
        
        # Detect charts and graphs
        charts = self._detect_charts(img_cv)
        elements.extend(self._process_charts(charts, page_num))
        
        # Save the processed elements
        self.extracted_elements.extend(elements)
        
        return elements

    def _detect_tables(self, img: np.ndarray) -> List[np.ndarray]:
        """Detect table regions in the image."""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours that might be tables
        tables = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > img.shape[1] * 0.3 and h > img.shape[0] * 0.1:  # Min size threshold
                tables.append(img[y:y+h, x:x+w])
        
        return tables

    def _detect_charts(self, img: np.ndarray) -> List[np.ndarray]:
        """Detect chart regions in the image."""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours that might be charts
        charts = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > img.shape[1] * 0.2 and h > img.shape[0] * 0.2:  # Min size threshold
                roi = img[y:y+h, x:x+w]
                if self._is_likely_chart(roi):
                    charts.append(roi)
        
        return charts

    def _is_likely_chart(self, img: np.ndarray) -> bool:
        """Determine if an image region is likely to be a chart."""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate the number of edges
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = np.count_nonzero(edges)
        
        # Calculate edge density
        total_pixels = img.shape[0] * img.shape[1]
        edge_density = edge_pixels / total_pixels
        
        # If edge density is within a certain range, it's likely a chart
        return 0.05 < edge_density < 0.5

    def _process_tables(self, tables: List[np.ndarray], page_num: int) -> List[Dict[str, Any]]:
        """Process detected tables using OCR and structure analysis."""
        processed_tables = []
        
        for idx, table_img in enumerate(tables):
            # Convert to PIL Image for OCR
            pil_image = Image.fromarray(cv2.cvtColor(table_img, cv2.COLOR_BGR2RGB))
            
            # Extract text using OCR
            text = pytesseract.image_to_string(pil_image)
            
            # Save table image
            table_path = self.temp_dir / f"table_{page_num}_{idx}.png"
            cv2.imwrite(str(table_path), table_img)
            
            processed_tables.append({
                'type': 'table',
                'page': page_num,
                'content': text,
                'image_path': str(table_path),
                'position': idx
            })
        
        return processed_tables

    def _process_charts(self, charts: List[np.ndarray], page_num: int) -> List[Dict[str, Any]]:
        """Process detected charts and analyze them using GPT-4 Vision."""
        processed_charts = []
        
        for idx, chart_img in enumerate(charts):
            # Save chart image
            chart_path = self.temp_dir / f"chart_{page_num}_{idx}.png"
            cv2.imwrite(str(chart_path), chart_img)
            
            # Convert image to base64 for GPT-4 Vision
            _, buffer = cv2.imencode('.png', chart_img)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            
            # Analyze chart using GPT-4 Vision
            try:
                analysis = self._analyze_chart_with_gpt4(base64_image)
            except Exception as e:
                analysis = f"Error analyzing chart: {str(e)}"
            
            processed_charts.append({
                'type': 'chart',
                'page': page_num,
                'analysis': analysis,
                'image_path': str(chart_path),
                'position': idx
            })
        
        return processed_charts

    def _analyze_chart_with_gpt4(self, base64_image: str) -> str:
        """Analyze a chart using GPT-4 Vision API."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this chart from an annual report. Describe its type, key trends, and main insights. Focus on financial implications."
                            },
                            {
                                "type": "image_url",
                                "image_url": f"data:image/png;base64,{base64_image}"
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing chart: {str(e)}"

    def get_extracted_elements(self) -> List[Dict[str, Any]]:
        """Get all extracted visual elements."""
        return self.extracted_elements

    def cleanup(self):
        """Clean up temporary files."""
        for file in self.temp_dir.glob("*"):
            file.unlink()
        self.temp_dir.rmdir() 