import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import re
from typing import List, Dict, Any, Union
import numpy as np
from io import BytesIO
import base64

class VisualizationProcessor:
    def __init__(self):
        """Initialize the visualization processor."""
        self.supported_chart_types = ['line', 'bar', 'pie', 'scatter']
        # Use a standard matplotlib style instead of seaborn
        plt.style.use('default')
        # Set some nice default parameters
        plt.rcParams['figure.figsize'] = [10, 6]
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10

    def extract_numerical_data(self, text: str) -> Dict[str, List[Union[str, float]]]:
        """Extract numerical data from text."""
        # Find patterns like "Revenue: $1.2M" or "Growth: 15%"
        number_pattern = r'(\d+\.?\d*)\s*[KMB%]?'
        label_pattern = r'([A-Za-z\s]+):'
        
        numbers = re.findall(number_pattern, text)
        labels = re.findall(label_pattern, text)
        
        return {
            'labels': labels,
            'values': [float(num) for num in numbers[:len(labels)]]
        }

    def create_visualization(self, data: Dict[str, List[Union[str, float]]], chart_type: str = 'bar') -> str:
        """Create visualization based on extracted data."""
        if not data['labels'] or not data['values']:
            return None

        plt.figure()
        
        if chart_type == 'bar':
            plt.bar(data['labels'], data['values'], color='skyblue')
            plt.xticks(rotation=45, ha='right')
        elif chart_type == 'line':
            plt.plot(data['labels'], data['values'], marker='o', color='steelblue', linewidth=2)
            plt.xticks(rotation=45, ha='right')
        elif chart_type == 'pie':
            plt.pie(data['values'], labels=data['labels'], autopct='%1.1f%%', 
                   colors=plt.cm.Pastel1(np.linspace(0, 1, len(data['labels']))))
        elif chart_type == 'scatter':
            if len(data['values']) > 1:
                x = range(len(data['values']))
                plt.scatter(x, data['values'], color='steelblue', alpha=0.6)
                plt.xticks(x, data['labels'], rotation=45, ha='right')

        plt.title(f"{chart_type.capitalize()} Chart", pad=20)
        plt.tight_layout()

        # Convert plot to base64 string
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()

        return base64.b64encode(image_png).decode()

    def detect_chart_type(self, text: str) -> str:
        """Detect the most appropriate chart type based on text content."""
        text = text.lower()
        
        # Check for time-series or trend-related keywords
        if any(word in text for word in ['trend', 'over time', 'growth', 'year', 'month']):
            return 'line'
        
        # Check for comparison-related keywords
        if any(word in text for word in ['compare', 'versus', 'distribution']):
            return 'bar'
        
        # Check for percentage or composition-related keywords
        if any(word in text for word in ['percentage', 'proportion', 'share', 'breakdown']):
            return 'pie'
        
        # Check for correlation or relationship-related keywords
        if any(word in text for word in ['correlation', 'relationship', 'scatter']):
            return 'scatter'
        
        # Default to bar chart
        return 'bar'

    def process_text_for_visualization(self, text: str) -> Dict[str, Any]:
        """Process text and create appropriate visualizations."""
        # Extract numerical data
        data = self.extract_numerical_data(text)
        
        if not data['labels'] or not data['values']:
            return None
        
        # Detect appropriate chart type
        chart_type = self.detect_chart_type(text)
        
        # Create visualization
        visualization = self.create_visualization(data, chart_type)
        
        if visualization:
            return {
                'chart_type': chart_type,
                'data': data,
                'visualization': visualization
            }
        
        return None 