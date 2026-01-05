"""Vision-language inference helpers using an Ollama VLM endpoint."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

from .contracts import FieldCandidate, PageInfo

DEFAULT_PROMPT = """You are an expert invoice parser. Extract the following fields as JSON with keys:
- supplier (string)
- invoice_number (string)
- invoice_date (ISO 8601 date string, e.g., 2024-01-31)
- total_amount (numeric string)
- currency (3-letter code)

Return ONLY a JSON object with those keys. If a field is missing, use an empty string."""


def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _build_message(prompt: str, image_paths: Iterable[Path]) -> List[dict]:
    content: List[dict] = [{"type": "text", "text": prompt}]
    for img in image_paths:
        content.append({"type": "image", "image": _encode_image(img)})
    return [{"role": "user", "content": content}]


def _parse_json_response(text: str) -> Dict[str, str]:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to recover a JSON object in free-form text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
    return {}


def infer_invoice_with_ollama(
    pages: List[PageInfo],
    prompt: str = DEFAULT_PROMPT,
    *,
    model: str = "qwen3-vl:4b",
    base_url: str = "http://localhost:11434",
    temperature: float = 0.0,
) -> Tuple[List[FieldCandidate], Dict[str, str]]:
    """Send rendered page images to Ollama VLM and parse invoice fields."""

    if not pages:
        return [], {"vlm_error": "no_pages"}

    image_paths = [Path(p.preprocessed_path or p.source_path) for p in pages if p.source_path]
    if not image_paths:
        return [], {"vlm_error": "no_images"}

    payload = {
        "model": model,
        "messages": _build_message(prompt, image_paths),
        "temperature": temperature,
        "stream": False,
    }
    meta: Dict[str, str] = {
        "vlm_model": model,
        "vlm_base_url": base_url,
        "vlm_error": "",
    }

    try:
        resp = requests.post(f"{base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content") or ""
        parsed = _parse_json_response(content)
    except Exception as exc:  # pragma: no cover - network/remote failures
        meta["vlm_error"] = f"vlm_error:{exc}"
        return [], meta

    fields: List[FieldCandidate] = []
    for key in ["supplier", "invoice_number", "invoice_date", "total_amount", "currency"]:
        value = parsed.get(key, "")
        fields.append(FieldCandidate(name=key, value=str(value) if value is not None else ""))

    return fields, meta
