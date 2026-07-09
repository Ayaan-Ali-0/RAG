"""NVIDIA Nemotron OCR v2 Engine Implementation for RAG core."""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from rbs_rag.ocr.engines.base import BaseOCREngine

logger = logging.getLogger(__name__)


class NemotronOCREngine(BaseOCREngine):
    """NVIDIA Nemotron OCR v2 engine - calls NVIDIA NIM API."""

    def __init__(self, api_key: str = "", base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._available = None

    @property
    def name(self) -> str:
        return "NemotronOCR"

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

    def extract_text(self, image_path: Path) -> dict[str, Any]:
        if not self.is_available():
            return {"text": "", "regions": [], "words": [], "error": "Nemotron engine not available"}
        return self._call_nemotron(image_path)

    def extract_text_from_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        if not self.is_available():
            return {"text": "", "regions": [], "words": [], "error": "Nemotron engine not available"}
        return self._call_nemotron_bytes(image_bytes)

    def process_pdf(self, pdf_bytes: bytes, filename: str) -> list[dict[str, Any]]:
        """Process PDF by converting pages to images and calling Nemotron."""
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                result = self.extract_text_from_bytes(img_bytes)
                pages.append({
                    "page_number": page_num + 1,
                    "text": result.get("text", ""),
                    "markdown": result.get("markdown", result.get("text", "")),
                    "words": result.get("words", []),
                    "regions": result.get("regions", []),
                    "word_count": len(result.get("words", [])),
                    "confidence": result.get("confidence", 0.0),
                })
            doc.close()
            return pages
        except Exception as e:
            logger.error("Nemotron PDF processing failed: %s", e)
            return []

    def _call_nemotron(self, image_path: Path) -> dict[str, Any]:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return self._call_nemotron_api(image_b64)

    def _call_nemotron_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return self._call_nemotron_api(image_b64)

    def _call_nemotron_api(self, image_b64: str) -> dict[str, Any]:
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

    def _parse_response(self, data: dict) -> dict[str, Any]:
        text_parts = []
        words = []
        regions = []

        output = data.get("output", data.get("text", ""))
        if isinstance(output, str):
            text_parts.append(output)
            words = output.split()
        elif isinstance(output, list):
            for item in output:
                t = item.get("text", "") if isinstance(item, dict) else str(item)
                text_parts.append(t)
                words.extend(t.split())

        return {
            "text": "\n".join(text_parts),
            "markdown": "\n".join(text_parts),
            "regions": regions,
            "words": words,
            "confidence": 1.0 if text_parts else 0.0,
        }
