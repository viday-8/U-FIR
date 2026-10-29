import io

from conftest import case_id, client, hdr

from app.services.ocr import language_of

CASE = "EXC/NRP/041/2025"


def make_png(text="Seized 120 bottles of NDPL"):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1100, 160), "white")
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
    except OSError:
        font = ImageFont.load_default(44)
    ImageDraw.Draw(img).text((20, 40), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def upload(user, name, data, doc_type="seizure"):
    r = client.post("/api/v1/ingest", headers=hdr(user), data={"case_id": case_id(CASE), "doc_type": doc_type}, files={"file": (name, data)})
    assert r.status_code == 202, r.text
    return r.json()["document_id"]


def test_scanned_image_is_ocr_marked_and_sent_to_review():
    doc_id = upload("inv_vizag", "scan.png", make_png())
    d = client.get(f"/api/v1/documents/{doc_id}", headers=hdr("inv_vizag")).json()
    assert d["has_ocr"] and d["pages"][0]["ocr"] and "120" in d["pages"][0]["text"]
    assert d["status"] == "needs_review"  # OCR text is never silently trusted
    assert client.get(f"/api/v1/ingest/{doc_id}", headers=hdr("inv_vizag")).json()["status"] == "needs_review"


def test_scanned_pdf_uses_ocr_but_text_pdf_does_not():
    from PIL import Image
    png = Image.open(io.BytesIO(make_png("Seized 77 bottles")))
    buf = io.BytesIO()
    png.save(buf, "PDF")
    doc_id = upload("inv_vizag", "scan.pdf", buf.getvalue())
    d = client.get(f"/api/v1/documents/{doc_id}", headers=hdr("inv_vizag")).json()
    assert d["has_ocr"] and "77" in d["pages"][0]["text"]


def test_blank_image_is_rejected_with_a_clear_message():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (400, 100), "white").save(buf, "PNG")
    r = client.post("/api/v1/ingest", headers=hdr("inv_vizag"), data={"case_id": case_id(CASE)}, files={"file": ("blank.png", buf.getvalue())})
    assert r.status_code == 422 and "No readable text" in r.json()["detail"]


def test_language_detection_and_telugu_goes_to_review():
    assert language_of("Seized 120 bottles") == "en"
    assert language_of("స్వాధీనం చేసుకున్న మద్యం") == "te"
    assert language_of("Seized మద్యం bottles 120 మరియు వాహనం") == "mixed"
    doc_id = upload("inv_vizag", "te.txt", "స్వాధీనం చేసుకున్న మద్యం 120 సీసాలు".encode(), "diary")
    d = client.get(f"/api/v1/documents/{doc_id}", headers=hdr("inv_vizag")).json()
    assert d["language"] == "te" and d["status"] == "needs_review"
