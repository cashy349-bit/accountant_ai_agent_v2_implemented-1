from PIL import Image
import pytesseract
from pathlib import Path
from hashlib import sha256
from pypdf import PdfReader

ALLOWED = {".pdf",".png",".jpg",".jpeg",".txt"}

def fingerprint(path):
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_text(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".txt":
        return Path(path).read_text(errors="replace")
    if suffix in {".png",".jpg",".jpeg"}:
        raise NotImplementedError("OCR adapter required for image documents.")
    raise ValueError("Unsupported file type")


def extract_image_text(path):
    """Preprocess an invoice image and extract text with Tesseract OCR."""
    image = Image.open(path).convert("L")

    # Upscale small invoice images for better character recognition.
    image = image.resize((image.width * 2, image.height * 2))

    # Improve contrast and create a clean black/white image.
    image = image.point(lambda pixel: 255 if pixel > 180 else 0)

    return pytesseract.image_to_string(
        image,
        config="--psm 6"
    )
