"""
Vercel Blob Storage Service
Handles downloading and processing PDFs stored in Vercel Blob
"""
import io
import httpx
from typing import Optional
from app.core.config import settings


class VercelBlobService:
    """
    Service for interacting with Vercel Blob Storage
    Downloads and processes resume PDFs from Vercel Blob URLs
    """
    
    def __init__(self):
        self.base_url = settings.VERCEL_BLOB_BASE_URL
        self.token = settings.VERCEL_BLOB_READ_WRITE_TOKEN
    
    def download_pdf(self, url: str) -> Optional[bytes]:
        """
        Download a PDF file from Vercel Blob storage
        
        Args:
            url: Full URL or relative path to the PDF
            
        Returns:
            PDF content as bytes, or None if download fails
        """
        try:
            # Handle both full URLs and relative paths
            if not url:
                return None
            
            # If it's a relative path, construct full URL
            if url.startswith('/'):
                # Remove leading slash and construct URL
                url = f"{self.base_url}/{url.lstrip('/')}"
            elif not url.startswith('http'):
                url = f"{self.base_url}/{url}"
            
            # Download the file
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                
                if response.status_code == 200:
                    return response.content
                else:
                    print(f"Failed to download PDF: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"Error downloading PDF from Vercel Blob: {e}")
            return None
    
    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes using pdfplumber
        
        Args:
            pdf_bytes: PDF content as bytes
            
        Returns:
            Extracted text from the PDF
        """
        try:
            import pdfplumber
            
            # Create a file-like object from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            
            text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def get_cv_text_from_url(self, url: str) -> str:
        """
        Download PDF from Vercel Blob and extract text
        
        Args:
            url: URL to the PDF in Vercel Blob storage
            
        Returns:
            Extracted text from the CV/Resume
        """
        if not url:
            return ""
        
        # Skip if URL is NULL or empty
        if url.upper() == "NULL":
            return ""
        
        # Download the PDF
        pdf_bytes = self.download_pdf(url)
        
        if not pdf_bytes:
            return ""
        
        # Extract text
        return self.extract_text_from_pdf_bytes(pdf_bytes)
    
    def upload_pdf(self, file_content: bytes, filename: str) -> Optional[str]:
        """
        Upload a PDF to Vercel Blob storage
        
        Args:
            file_content: PDF content as bytes
            filename: Name for the uploaded file
            
        Returns:
            URL of the uploaded file, or None if upload fails
        """
        try:
            # Vercel Blob API endpoint
            upload_url = "https://blob.vercel-storage.com"
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/pdf",
                "x-api-version": "7"
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.put(
                    f"{upload_url}/resumes/{filename}",
                    content=file_content,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    return result.get("url", result.get("pathname"))
                else:
                    print(f"Failed to upload PDF: HTTP {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error uploading PDF to Vercel Blob: {e}")
            return None


# Singleton instance
vercel_blob_service = VercelBlobService()
