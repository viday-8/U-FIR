"""OCR for scanned pages using RapidOCR (open source, pip-only). OCR text is always marked as OCR and the
document is sent to review, because machine-read text can contain errors."""
from io import BytesIO

_engine = None


def _get():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def ocr_image(image) -> str:
    import numpy as np
    result, _ = _get()(np.array(image.convert("RGB")))
    if not result:
        return ""
    lines = sorted(result, key=lambda r: (round(sum(p[1] for p in r[0]) / 4 / 18), sum(p[0] for p in r[0]) / 4))  # row, then x
    rows, last = [], None
    for box, text, _conf in lines:
        row = round(sum(p[1] for p in box) / 4 / 18)
        if row == last and rows:
            rows[-1] += " " + text
        else:
            rows.append(text)
        last = row
    return "\n".join(rows)


def ocr_pdf_page(data: bytes, index: int) -> str:
    import pypdfium2 as pdfium
    page = pdfium.PdfDocument(data)[index]
    return ocr_image(page.render(scale=2.5).to_pil())


def ocr_image_bytes(data: bytes) -> str:
    from PIL import Image
    return ocr_image(Image.open(BytesIO(data)))


def telugu_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum("ఀ" <= c <= "౿" for c in letters) / len(letters) if letters else 0.0


def language_of(text: str) -> str:
    s = telugu_share(text)
    return "te" if s > 0.6 else "mixed" if s > 0.05 else "en"
