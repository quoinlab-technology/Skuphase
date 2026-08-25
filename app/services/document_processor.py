"""Document processing service for PDF extraction and chunking."""

import re
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import PyPDF2
import tiktoken

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents (PDFs) to extract text and create chunks."""
    
    # Token limits for chunking
    CHUNK_SIZE_TOKENS = 256  # ~1000 characters per chunk
    CHUNK_OVERLAP_TOKENS = 50  # 50 token overlap for context
    
    def __init__(self):
        """Initialize the document processor."""
        self.encoding = tiktoken.get_encoding("cl100k_base")

    @staticmethod
    def _extract_images_from_pdf(
        file_path: str,
        output_dir: str,
        enable_ocr: bool = True,
    ) -> List[Dict[str, Any]]:
        """Extract embedded images from PDF into files with optional OCR text."""
        try:
            import fitz  # type: ignore
        except Exception:
            logger.info("PyMuPDF (fitz) not available; skipping PDF image extraction")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        extracted: List[Dict[str, Any]] = []
        pdf = fitz.open(file_path)
        try:
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                page_images = page.get_images(full=True)
                for image_index, image in enumerate(page_images, start=1):
                    xref = image[0]
                    data = pdf.extract_image(xref)
                    image_bytes = data.get("image")
                    if not image_bytes:
                        continue
                    ext = data.get("ext", "png")
                    file_name = f"page_{page_index + 1:03d}_img_{image_index:03d}.{ext}"
                    file_path_out = output_path / file_name
                    with open(file_path_out, "wb") as output_file:
                        output_file.write(image_bytes)

                    ocr_text = None
                    if enable_ocr:
                        ocr_text = DocumentProcessor._extract_ocr_text(str(file_path_out))

                    extracted.append(
                        {
                            "page_number": page_index + 1,
                            "image_index": image_index,
                            "file_name": file_name,
                            "file_path": str(file_path_out).replace("\\", "/"),
                            "ocr_text": ocr_text,
                        }
                    )
        finally:
            pdf.close()

        logger.info("Extracted %s images from PDF %s", len(extracted), file_path)
        return extracted

    @staticmethod
    def _extract_ocr_text(image_path: str) -> Optional[str]:
        """Run OCR on an image.

        Uses PaddleOCR (Baidu, Apache-2.0) when available: it significantly
        outperforms Tesseract on non-English, multi-column and handwritten
        text - the typical profile of scanned Nigerian WAEC/NECO past papers
        and curriculum PDFs. Falls back to pytesseract if PaddleOCR is absent.
        """
        try:
            from PIL import Image
            import paddleocr  # type: ignore
        except Exception:
            return DocumentProcessor._extract_ocr_text_tesseract(image_path)

        try:
            # Lazy singleton avoids reloading the model on every call.
            if not hasattr(DocumentProcessor, "_paddle_ocr"):
                DocumentProcessor._paddle_ocr = paddleocr.PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    show_log=False,
                )
            ocr = DocumentProcessor._paddle_ocr
            result = ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return None
            lines = [line[1][0] for line in result[0] if line and line[1]]
            text = "\n".join(lines).strip()
            return text if text else None
        except Exception as exc:
            logger.warning("PaddleOCR failed for %s (%s); trying Tesseract", image_path, exc)
            return DocumentProcessor._extract_ocr_text_tesseract(image_path)

    @staticmethod
    def _extract_ocr_text_tesseract(image_path: str) -> Optional[str]:
        """Tesseract fallback OCR."""
        try:
            from PIL import Image
            import pytesseract  # type: ignore
        except Exception:
            return None

        try:
            text = pytesseract.image_to_string(Image.open(image_path)).strip()
            return text if text else None
        except Exception:
            logger.warning("Tesseract OCR extraction failed for image: %s", image_path)
            return None
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            ValueError: If PDF cannot be read
        """
        try:
            text = ""
            page_count = 0
            
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")
                        continue
            
            if not text.strip():
                # Scanned PDF (no embedded text layer): OCR each page.
                logger.info("No embedded text in PDF %s; running page OCR", file_path)
                text, page_count = DocumentProcessor._ocr_pdf_pages(file_path)
                if not text.strip():
                    raise ValueError("No text could be extracted from PDF")
                return text, page_count

            logger.info(f"Extracted {page_count} pages from PDF: {file_path}")
            return text, page_count

        except FileNotFoundError:
            raise ValueError(f"PDF file not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    @staticmethod
    def _ocr_pdf_pages(file_path: str) -> tuple[str, int]:
        """OCR every page of a scanned PDF using PaddleOCR (pytesseract fallback)."""
        try:
            import fitz  # type: ignore
        except Exception:
            return "", 0

        pdf = fitz.open(file_path)
        page_count = len(pdf)
        pages_text: List[str] = []
        for page_index in range(page_count):
            page = pdf[page_index]
            pix = page.get_pixmap(dpi=200)
            tmp_path = f"{file_path}.page{page_index + 1}.png"
            pix.save(tmp_path)
            try:
                ocr_text = DocumentProcessor._extract_ocr_text(tmp_path)
                if ocr_text:
                    pages_text.append(f"\n--- Page {page_index + 1} ---\n{ocr_text}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        pdf.close()
        return "\n".join(pages_text), page_count
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text for better chunking.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove multiple blank lines
        text = re.sub(r'[ \t]+', ' ', text)  # Collapse multiple spaces
        text = text.strip()
        
        return text
    
    def split_into_chunks(
        self,
        text: str,
        chunk_size_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
    ) -> List[str]:
        """
        Split text into semantic chunks with token-based sizing.
        
        Uses a simple approach that respects sentence boundaries.
        For production, consider using sentence-transformers or spaCy.
        
        Args:
            text: Full document text
            chunk_size_tokens: Target tokens per chunk
            overlap_tokens: Token overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size_tokens or self.CHUNK_SIZE_TOKENS
        overlap = overlap_tokens or self.CHUNK_OVERLAP_TOKENS
        
        # Split into sentences (basic approach)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # If adding this sentence exceeds chunk size, save current chunk
            if current_tokens + sentence_tokens > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start overlap with last few sentences
                overlap_sentences = []
                temp_tokens = 0
                temp_text = current_chunk
                
                for prev_sentence in reversed(sentences):
                    if prev_sentence in temp_text:
                        prev_tokens = len(self.encoding.encode(prev_sentence))
                        if temp_tokens + prev_tokens <= overlap:
                            overlap_sentences.insert(0, prev_sentence)
                            temp_tokens += prev_tokens
                        else:
                            break
                
                current_chunk = " ".join(overlap_sentences)
                current_tokens = temp_tokens
            
            current_chunk += " " + sentence if current_chunk else sentence
            current_tokens = len(self.encoding.encode(current_chunk))
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        logger.info(f"Split document into {len(chunks)} chunks")
        return chunks
    
    def process_pdf(
        self,
        file_path: str,
        asset_output_dir: Optional[str] = None,
        extract_images: bool = True,
        enable_ocr: bool = True,
    ) -> Dict[str, Any]:
        """
        Complete PDF processing pipeline.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Processing result with text, chunks, metadata
        """
        try:
            # Extract text
            full_text, page_count = self.extract_text_from_pdf(file_path)
            
            # Clean text
            cleaned_text = self.clean_text(full_text)
            
            # Split into chunks
            chunks = self.split_into_chunks(cleaned_text)
            extracted_images: List[Dict[str, Any]] = []
            if extract_images and asset_output_dir:
                extracted_images = self._extract_images_from_pdf(
                    file_path=file_path,
                    output_dir=asset_output_dir,
                    enable_ocr=enable_ocr,
                )
            
            return {
                "success": True,
                "full_text": cleaned_text,
                "chunks": chunks,
                "page_count": page_count,
                "chunk_count": len(chunks),
                "extracted_images": extracted_images,
                "image_count": len(extracted_images),
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            return {
                "success": False,
                "full_text": "",
                "chunks": [],
                "page_count": 0,
                "chunk_count": 0,
                "extracted_images": [],
                "image_count": 0,
                "error": str(e),
            }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using cl100k_base encoding."""
        return len(self.encoding.encode(text))
    
    def estimate_chunk_count(self, file_path: str) -> int:
        """Estimate number of chunks from file without full processing."""
        try:
            text, _ = self.extract_text_from_pdf(file_path)
            cleaned = self.clean_text(text)
            token_count = self.count_tokens(cleaned)
            
            # Estimate chunks based on chunk size and overlap
            estimated_chunks = max(1, token_count // (self.CHUNK_SIZE_TOKENS - self.CHUNK_OVERLAP_TOKENS))
            return estimated_chunks
            
        except Exception as e:
            logger.warning(f"Failed to estimate chunk count: {str(e)}")
            return 0
