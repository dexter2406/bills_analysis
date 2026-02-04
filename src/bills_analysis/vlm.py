"""Vision-language inference helpers using an Ollama VLM endpoint."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

from .contracts import FieldCandidate, PageInfo


fields_beleg = ["brutto", "netto", "store_name", "total_tax", "run_date"]
fields_zbon = ["brutto", "netto", "store_name", "total_tax", "run_date"]

prompt_beleg = f"""
You are an expert invoice and receipt parser.

Return ONLY valid JSON with exactly these keys:
{fields_beleg}

Rules:
- Monetary values must be strings using comma or dot as in the document (e.g. "9,98" or "9.98").
- run_date must be ISO format (YYYY-MM-DD) if present.
- If a value is unknown, use an empty string "".

Example:
{{"brutto":"8,94","netto":"8,36","store_name":"REWE","total_tax":"0,58","run_date":"2025-08-15"}}
"""

prompt_zbon = f"""
You are an expert receipt parser.

Return ONLY valid JSON with exactly these keys:
{fields_zbon}

Rules:
- brutto may appear as "Tagesumsatz" or "Gesamtbetrag".
- netto may appear as "Nettoumsatz".
- run_date must be ISO format (YYYY-MM-DD) if present.
- If a value is unknown, use an empty string "".

Example:
{{"brutto":"1234.56","netto":"987.65","store_name":"REWE","total_tax":"246.91","run_date":"2025-08-15"}}
"""

prompts_dict = {
    "beleg": {"fields": fields_beleg, "prompt": prompt_beleg},
    "zbon": {"fields": fields_zbon, "prompt": prompt_zbon},
}

DEFAULT_PROMPT = prompt_beleg

def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _build_message(prompt: str, image_paths: Iterable[Path]) -> List[dict]:
    images = [_encode_image(img) for img in image_paths]
    return [{"role": "user", "content": prompt, "images": images}]


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
    purpose: str,
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
        "messages": _build_message(prompts_dict[purpose]["prompt"], image_paths),
        "temperature": temperature,
        "stream": False,
    }
    meta: Dict[str, str] = {
        "vlm_model": model,
        "vlm_base_url": base_url,
        "vlm_error": "",
    }

    try:
        start = time.perf_counter()
        resp = requests.post(f"{base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content") or ""
        parsed = _parse_json_response(content)
        elapsed = time.perf_counter() - start
        print(f"VLM request time: {elapsed:.2f}s")
    except Exception as exc:  # pragma: no cover - network/remote failures
        meta["vlm_error"] = f"vlm_error:{exc}"
        return [], meta

    fields: List[FieldCandidate] = []
    for key in prompts_dict[purpose]["fields"]:
        value = parsed.get(key, "")
        fields.append(FieldCandidate(name=key, value=str(value) if value is not None else ""))

    return fields, meta
