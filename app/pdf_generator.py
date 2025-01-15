from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
import io
import re
import tempfile
import os
import base64
from datetime import datetime
from pathlib import Path
import json
import requests  # We'll use this for the Mermaid API

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#232F3E'),  # AWS Dark Blue
        )
        
        # Section header style
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#FF9900'),  # AWS Orange
            borderWidth=1,
            borderColor=colors.HexColor('#FF9900'),
            borderPadding=(10, 0, 10, 0),
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'BodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
        )
        
        # Bullet style
        self.bullet_style = ParagraphStyle(
            'BulletText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=5,
        )

        # Footer style
        self.footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceBefore=30
        )

    def _format_section(self, title: str, content: str) -> list:
        """Format a section with title and content"""
        elements = []
        elements.append(Paragraph(title, self.section_style))
        
        # Split content into paragraphs
        paragraphs = content.split('\n')
        for para in paragraphs:
            if para.strip():
                if para.strip().startswith('•'):
                    # Format bullet points
                    elements.append(Paragraph(para, self.bullet_style))
                else:
                    elements.append(Paragraph(para, self.body_style))
        
        return elements

    def _clean_and_structure_content(self, text: str) -> dict:
        """Clean markdown and structure the content into sections"""
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
        # Split into sections
        sections = {
            "Requirement Analysis": "",
            "Architecture Design": "",
            "Implementation Steps": "",
            "Cost Optimization": ""
        }
        
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            if any(section in line for section in sections.keys()):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                    current_content = []
                current_section = next((s for s in sections.keys() if s in line), None)
            elif current_section and line.strip():
                # Convert markdown bullets to bullet points
                if line.strip().startswith('-'):
                    line = '•' + line[1:]
                current_content.append(line.strip())
        
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections

    def _capture_diagram_image(self, mermaid_code: str) -> Image:
        """Generate diagram using Mermaid Live Editor API"""
        try:
            # Encode the Mermaid code
            graphbytes = mermaid_code.encode("utf-8")
            base64_graph = base64.b64encode(graphbytes).decode("utf-8")

            # Use the Mermaid Live Editor API to get the SVG
            api_url = f"https://mermaid.ink/img/{base64_graph}"
            response = requests.get(api_url)
            response.raise_for_status()

            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            # Create reportlab Image
            img = Image(tmp_path)
            
            # Set size while maintaining aspect ratio
            aspect = img.imageWidth / img.imageHeight
            target_width = 6 * inch  # Slightly smaller than page width
            img.drawWidth = target_width
            img.drawHeight = target_width / aspect

            # Clean up the temporary file
            os.unlink(tmp_path)

            return img

        except Exception as e:
            raise Exception(f"Failed to capture diagram: {str(e)}")

    def generate_pdf(self, recommendation: str, mermaid_code: str, user_input: str) -> bytes:
        """Generate PDF with improved formatting"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
            title="AWS Infrastructure Design Document"
        )
        
        content = []
        
        try:
            # Add title and date
            title_text = f"AWS Infrastructure Design Document\n{datetime.now().strftime('%B %d, %Y')}"
            content.append(Paragraph(title_text, self.title_style))
            content.append(Spacer(1, 20))
            
            # Add user requirements
            content.append(Paragraph("User Requirements", self.section_style))
            content.append(Paragraph(user_input, self.body_style))
            content.append(Spacer(1, 20))
            
            # Add recommendation content
            sections = self._clean_and_structure_content(recommendation)
            for section_title, section_content in sections.items():
                if section_content:
                    content.extend(self._format_section(section_title, section_content))
                    content.append(Spacer(1, 20))
            
            # Add architecture diagram
            content.append(Paragraph("Architecture Diagram", self.section_style))
            try:
                diagram_image = self._capture_diagram_image(mermaid_code)
                content.append(diagram_image)
            except Exception as e:
                content.append(Paragraph(f"Note: Could not include diagram due to: {str(e)}", self.body_style))
            
            content.append(Spacer(1, 20))
            
            # Add footer
            footer_text = "Generated by AWS Infrastructure Planner"
            content.append(Paragraph(footer_text, self.footer_style))
            
            # Build PDF
            doc.build(content)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Error generating PDF: {str(e)}")
