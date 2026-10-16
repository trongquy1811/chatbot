from io import BytesIO
from pathlib import Path
from typing import Any
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.config import Settings
from backend.services.gemini import Gemini

ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".markdown",
    ".png", ".jpg", ".jpeg",
}


def analyze_image(data: bytes, ai: Gemini) -> str:
    """Validate and transcribe image data using Gemini Vision."""
    try:
        with Image.open(BytesIO(data)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError("Image exceeds 20 megapixels limit")

            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="JPEG")
            return ai.vision(buffer.getvalue(), "image/jpeg")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid or corrupted/oversized image") from exc


def parse_document(
    data: bytes,
    name: str,
    ai: Gemini,
    settings: Settings,
    analyze_all_images: bool = False,
) -> list[dict[str, Any]]:
    """
    Parse document content, handle text and images, and divide into structured chunks.
    Only analyzes PDF images when requested or enabled via settings.
    """
    suffix = Path(name).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported formats: PDF, TXT, MD, PNG, JPG"
        )

    pages: list[tuple[int, str]] = []

    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF file signature")

        reader = PdfReader(BytesIO(data))

        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")

        if len(reader.pages) > settings.max_pdf_pages:
            raise ValueError(
                f"PDF exceeds maximum page limit of {settings.max_pdf_pages} pages"
            )

        should_ocr_images = analyze_all_images or settings.ocr_pdf_images

        for number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            # Only read images in PDF when needed or requested
            if should_ocr_images:
                images = list(page.images)
                if len(images) > 4:
                    raise ValueError(
                        f"Page {number} has {len(images)} embedded images; maximum allowed is 4"
                    )

                for image in images:
                    page_text += "\n" + analyze_image(image.data, ai)

            if page_text.strip():
                pages.append((number, page_text))

    elif suffix in {".png", ".jpg", ".jpeg"}:
        pages.append((1, analyze_image(data, ai)))

    else:
        try:
            pages.append((1, data.decode("utf-8-sig")))
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must be encoded in UTF-8") from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=180,
    )

    chunks = [
        {"page": page_number, "text": chunk}
        for page_number, page_text in pages
        for chunk in splitter.split_text(page_text)
    ]

    if not chunks:
        raise ValueError("No readable text content found in document")

    if len(chunks) > settings.max_chunks:
        raise ValueError(
            f"Document produces {len(chunks)} chunks, exceeding max limit of {settings.max_chunks}"
        )

    return chunks
