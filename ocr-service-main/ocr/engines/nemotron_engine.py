"""NVIDIA Nemotron OCR v2 Engine Implementation for standalone microservice."""
from __future__ import annotations

import base64
import logging
import re
from typing import List

import httpx
from ocr.engines.base import BaseOCREngine
from schemas.ocr import PageResult, ExtractedEntities

logger = logging.getLogger(__name__)


class NemotronOCREngine(BaseOCREngine):
    """NVIDIA Nemotron OCR v2 engine — calls NVIDIA NIM API."""

    def __init__(self, api_key: str = "", base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._available = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not self.api_key:
            self._available = False
            return False
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def process_image(self, image_data: bytes, filename: str) -> PageResult:
        result = self._call_nemotron(image_data)
        text = result.get("text", "")
        md = result.get("markdown", text)
        words = text.split()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        return PageResult(
            page_number=1,
            full_text=text,
            markdown=md,
            tables=result.get("tables", []),
            hyperlinks=[],
            paragraphs=paragraphs,
            lines=lines,
            words=words,
            regions=[],
            entities=ExtractedEntities(),
        )

    def process_pdf(self, pdf_bytes: bytes, filename: str) -> List[PageResult]:
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages: List[PageResult] = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                result = self._call_nemotron(img_bytes)
                text = result.get("text", "")
                md = result.get("markdown", text)
                words_list = text.split()
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

                pages.append(PageResult(
                    page_number=page_num + 1,
                    full_text=text,
                    markdown=md,
                    tables=result.get("tables", []),
                    hyperlinks=[],
                    paragraphs=paragraphs,
                    lines=lines,
                    words=words_list,
                    regions=[],
                    entities=ExtractedEntities(),
                ))
            doc.close()
            return pages
        except Exception as e:
            logger.error("Nemotron PDF processing failed: %s", e)
            return [PageResult(
                page_number=1,
                full_text="",
                paragraphs=[],
                lines=[],
                words=[],
                regions=[],
                entities=ExtractedEntities(),
            )]

    def _call_nemotron(self, image_bytes: bytes) -> dict:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return self._call_nemotron_api(image_b64)

    def _call_nemotron_api(self, image_b64: str) -> dict:
        url = f"{self.base_url}/v1/infer"
        payload = {
            "input": [
                {
                    "type": "image_url",
                    "url": f"data:image/png;base64,{image_b64}"
                }
            ]
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data)
        except Exception as e:
            logger.error("Nemotron API call failed: %s", e)
            return {"text": "", "regions": [], "words": [], "error": str(e)}

    @staticmethod
    def _parse_response(data: dict) -> dict:
        text_parts = []
        output = data.get("output", data.get("text", ""))
        if isinstance(output, str):
            text_parts.append(output)
        elif isinstance(output, list):
            for item in output:
                t = item.get("text", "") if isinstance(item, dict) else str(item)
                text_parts.append(t)

        return {
            "text": "\n".join(text_parts),
            "markdown": "\n".join(text_parts),
            "tables": [],
            "regions": [],
            "words": "\n".join(text_parts).split(),
            "confidence": 1.0 if text_parts else 0.0,
        }
