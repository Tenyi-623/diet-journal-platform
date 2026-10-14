import base64
import tempfile
import unittest
from pathlib import Path

import pymupdf
from fastapi import HTTPException

from backend.app.admin import decode_upload
from backend.app.kb_import import extract_upload


class AdminFileTests(unittest.TestCase):
    def test_upload_size_and_encoding_limits(self):
        for value, limit in [
            ("%%%bad", 100),
            (base64.b64encode(b"x" * 101).decode(), 100),
        ]:
            with self.assertRaises(HTTPException):
                decode_upload(value, limit)

    def test_historical_pdf_remains_quarantined_with_blank_warning(self):
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text(
            (40, 60), "Synthetic historical document for import isolation tests. " * 3
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.pdf"
            pdf.save(path)
            pdf.close()
            doc = extract_upload(
                {
                    "file_path": str(path),
                    "sha256": "test",
                    "metadata": {
                        "title": "test",
                        "filename": "test.pdf",
                        "publisher": "test",
                        "edition": "test",
                        "source_kind": "historical_guideline",
                        "warning": "",
                    },
                }
            )
        self.assertFalse(doc["enabled"])
        self.assertTrue(all(p["status"] == "quarantined" for p in doc["pages"]))
