from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseOCREngine
from .paddle_engine import PaddleOCREngine
from .mistral_engine import MistralOCREngine
from .nemotron_engine import NemotronOCREngine


class OCROrchestrator:
    """Manages multiple OCR engines with fallback logic."""

    def __init__(self, engines: list[BaseOCREngine] = None):
        self.engines = engines or []
        self.primary_engine = None
        self.fallback_engines = []
        
        # Separate primary and fallback engines
        for engine in self.engines:
            if engine.is_available():
                if self.primary_engine is None:
                    self.primary_engine = engine
                else:
                    self.fallback_engines.append(engine)

    def add_engine(self, engine: BaseOCREngine):
        """Add an OCR engine to the orchestrator."""
        if engine.is_available():
            if self.primary_engine is None:
                self.primary_engine = engine
            else:
                self.fallback_engines.append(engine)

    def extract_text(self, image_path: Path) -> dict[str, Any]:
        """Extract text using primary engine with fallback."""
        if self.primary_engine:
            result = self.primary_engine.extract_text(image_path)
            if not result.get("error") and result.get("text", "").strip():
                result["engine"] = self.primary_engine.name
                return result

        # Try fallback engines
        for engine in self.fallback_engines:
            result = engine.extract_text(image_path)
            if not result.get("error") and result.get("text", "").strip():
                result["engine"] = engine.name
                return result

        # All engines failed
        return {"text": "", "regions": [], "words": [], "error": "All OCR engines failed", "engine": "none"}

    def extract_text_from_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        """Extract text from bytes using primary engine with fallback."""
        if self.primary_engine:
            result = self.primary_engine.extract_text_from_bytes(image_bytes)
            if not result.get("error") and result.get("text", "").strip():
                result["engine"] = self.primary_engine.name
                return result

        # Try fallback engines
        for engine in self.fallback_engines:
            result = engine.extract_text_from_bytes(image_bytes)
            if not result.get("error") and result.get("text", "").strip():
                result["engine"] = engine.name
                return result

        return {"text": "", "regions": [], "words": [], "error": "All OCR engines failed", "engine": "none"}

    def get_available_engines(self) -> list[str]:
        """Get list of available engine names."""
        names = []
        if self.primary_engine:
            names.append(self.primary_engine.name)
        names.extend(e.name for e in self.fallback_engines)
        return names


def create_orchestrator(
    mistral_api_key: str = "",
    languages: list[str] = None,
    use_gpu: bool = False,
    primary_engine: str = "nemotron",
    nemotron_api_key: str = "",
    nemotron_base_url: str = "http://localhost:8000",
) -> OCROrchestrator:
    """Create an OCR orchestrator with configured engines.

    Priority order: Nemotron -> Mistral -> Paddle
    """
    engines = []

    if primary_engine == "nemotron":
        # Try Nemotron first
        if nemotron_api_key:
            engines.append(NemotronOCREngine(api_key=nemotron_api_key, base_url=nemotron_base_url))
        # Then Mistral
        if mistral_api_key:
            engines.append(MistralOCREngine(api_key=mistral_api_key))
        # Then PaddleOCR as final fallback
        engines.append(PaddleOCREngine(languages=languages, use_gpu=use_gpu))
    elif primary_engine == "mistral":
        # Try Mistral first
        if mistral_api_key:
            engines.append(MistralOCREngine(api_key=mistral_api_key))
        # Nemotron second
        if nemotron_api_key:
            engines.append(NemotronOCREngine(api_key=nemotron_api_key, base_url=nemotron_base_url))
        # Then PaddleOCR as final fallback
        engines.append(PaddleOCREngine(languages=languages, use_gpu=use_gpu))
    else:
        # PaddleOCR first
        engines.append(PaddleOCREngine(languages=languages, use_gpu=use_gpu))
        if mistral_api_key:
            engines.append(MistralOCREngine(api_key=mistral_api_key))
        if nemotron_api_key:
            engines.append(NemotronOCREngine(api_key=nemotron_api_key, base_url=nemotron_base_url))

    return OCROrchestrator(engines)