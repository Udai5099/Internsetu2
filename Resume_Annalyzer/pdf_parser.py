import logging
import io
from typing import Optional
from streamlit.runtime.uploaded_file_manager import UploadedFile
import docx2txt
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextExtractionError(Exception):
    """Custom exception for text extraction errors"""
    pass

def extract_text_from_pdf_pypdf2(file_content: bytes) -> str:
    """
    Extract text from PDF using PyPDF2.
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        TextExtractionError: If extraction fails
    """
    try:
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)
        
        if reader.is_encrypted:
            logger.warning("PDF is encrypted, attempting to decrypt with empty password")
            try:
                reader.decrypt("")
            except Exception as e:
                raise TextExtractionError(f"PDF is encrypted and cannot be decrypted: {str(e)}")
        
        text_parts = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.warning(f"No text found on page {page_num + 1}")
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                continue
        
        if not text_parts:
            raise TextExtractionError("No text could be extracted from PDF")
            
        return "\n".join(text_parts)
        

    except PdfReadError as e:
        raise TextExtractionError(f"PDF file is corrupted or invalid: {str(e)}")
    except Exception as e:
        raise TextExtractionError(f"Unexpected error extracting PDF text: {str(e)}")

def extract_text_from_pdf_pdfplumber(file_content: bytes) -> str:
    """
    Extract text from PDF using pdfplumber (fallback method).
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        TextExtractionError: If extraction fails
    """
    try:
        import pdfplumber
        pdf_file = io.BytesIO(file_content)
        
        text_parts = []
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    else:
                        logger.warning(f"No text found on page {page_num + 1}")
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                    continue
        
        if not text_parts:
            raise TextExtractionError("No text could be extracted from PDF")
            
        return "\n".join(text_parts)
        
    except ImportError:
        raise TextExtractionError("pdfplumber is not installed. Install with: pip install pdfplumber")
    except Exception as e:
        raise TextExtractionError(f"Error extracting PDF text with pdfplumber: {str(e)}")

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF using PyPDF2 with pdfplumber fallback.
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        TextExtractionError: If both extraction methods fail
    """
    # Try PyPDF2 first
    try:
        logger.info("Attempting PDF text extraction with PyPDF2")
        return extract_text_from_pdf_pypdf2(file_content)
    except TextExtractionError as e:
        logger.warning(f"PyPDF2 extraction failed: {str(e)}")
        
        # Try pdfplumber as fallback
        try:
            logger.info("Attempting PDF text extraction with pdfplumber")
            return extract_text_from_pdf_pdfplumber(file_content)
        except TextExtractionError as e2:
            raise TextExtractionError(f"Both PyPDF2 and pdfplumber failed. PyPDF2: {str(e)}, pdfplumber: {str(e2)}")

def extract_text_from_docx(file_content: bytes) -> str:
    """
    Extract text from DOCX file.
    
    Args:
        file_content: DOCX file content as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        TextExtractionError: If extraction fails
    """
    try:
        docx_file = io.BytesIO(file_content)
        text = docx2txt.process(docx_file)
        
        if not text or not text.strip():
            raise TextExtractionError("No text could be extracted from DOCX file")
            
        return text.strip()
        
    except Exception as e:
        raise TextExtractionError(f"Error extracting DOCX text: {str(e)}")

def extract_text_from_file(uploaded_file: UploadedFile) -> str:
    """
    Extract text from uploaded file (PDF or DOCX).
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Extracted text as string
        
    Raises:
        TextExtractionError: If file type is unsupported or extraction fails
        ValueError: If uploaded_file is None or invalid
    """
    if not uploaded_file:
        raise ValueError("No file provided")
    
    if not hasattr(uploaded_file, 'name') or not hasattr(uploaded_file, 'read'):
        raise ValueError("Invalid file object provided")
    
    # Get file extension
    file_name = uploaded_file.name.lower()
    file_extension = file_name.split('.')[-1] if '.' in file_name else ''
    
    logger.info(f"Processing file: {uploaded_file.name} (type: {file_extension})")
    
    try:
        # Read file content
        file_content = uploaded_file.read()
        if not file_content:
            raise TextExtractionError("File is empty or could not be read")
        
        # Extract text based on file type
        if file_extension == 'pdf':
            return extract_text_from_pdf(file_content)
        elif file_extension in ['docx', 'doc']:
            return extract_text_from_docx(file_content)
        else:
            raise TextExtractionError(f"Unsupported file type: {file_extension}. Supported types: pdf, docx, doc")
            
    except TextExtractionError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing file {uploaded_file.name}: {str(e)}")
        raise TextExtractionError(f"Unexpected error processing file: {str(e)}")
