"""Vision-language inference helpers using an Ollama VLM endpoint."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

from .contracts import FieldCandidate, PageInfo


prompt_beleg = """
You are an expert invoice and receipt parser.

Your task:
Analyze the given image and return ONLY a single valid JSON object.
Do NOT include explanations, comments, or markdown.

--------------------------------------------------
STEP 1 — Document Type Detection
--------------------------------------------------
First, determine whether the document is:
(A) a scanned retail receipt (photo / thermal paper / noisy layout), or
(B) a structured electronic invoice (PDF-style layout, tables, aligned columns, e.g. Amazon).

Adjust your extraction strategy accordingly.

--------------------------------------------------
STEP 2 — Extraction Rules (apply to BOTH types)
--------------------------------------------------
- Focus ONLY on totals and tax summary areas.
- Ignore unit prices, per-item prices, quantities, SKUs, and line-item details.
- Prefer amounts that appear near keywords such as:
  "total", "gesamt", "gesamtpreis", "betrag", "zu zahlen", "amount due",
  "netto", "zwischensumme", "subtotal", "ohne ust",
  "mwst", "ust", "vat", "steuer".

--------------------------------------------------
STEP 3 — Priority Rules
--------------------------------------------------
Brutto (gross, incl. tax):
- Prefer amounts labeled or implied as:
  "Gesamt", "Gesamtpreis", "Total", "Tagesumsatz", "Amount Due".
- If multiple totals exist, prefer the one closest to the bottom of the document.
- If still ambiguous, choose the most prominent final payable amount.

Netto (net, excl. tax):
- Prefer amounts labeled or implied as:
  "Netto", "Zwischensumme (ohne USt.)", "Subtotal (excl. VAT)".
- Do NOT infer netto if no explicit or strongly implied net amount exists.

--------------------------------------------------
STEP 4 — Consistency Check (important)
--------------------------------------------------
- If both netto and a tax amount are visible, brutto should approximately equal:
  netto + tax (allow small rounding differences).
- If only brutto is clearly identifiable, leave netto empty.

--------------------------------------------------
STEP 5 — Output Constraints
--------------------------------------------------
Return ONLY valid JSON with exactly these keys:
["brutto","netto","score_brutto","score_netto","store_name"]

Formatting rules:
- Monetary values must be strings using comma or dot as in the document (e.g. "9,98" or "9.98").
- If a value is unknown, use an empty string "".

Scoring rules:
- score_brutto and score_netto MUST be one of: [-1, 0, 1].
- Use:
  1  = explicitly labeled and unambiguous
  0  = inferred or chosen among multiple candidates
  -1 = not found / cannot be determined

--------------------------------------------------
STEP 6 — Store Name
--------------------------------------------------
- store_name should be the merchant or seller name if clearly visible.
- If not identifiable, use "" and keep scores unchanged.

--------------------------------------------------
FINAL RULE
--------------------------------------------------
If multiple candidates exist:
- Choose the most likely one based on labels, position, and consistency.
- Set the corresponding score to 0.

--------------------------------------------------
Example output:
{"brutto":"8,94","netto":"8,36","score_brutto":1,"score_netto":1,"store_name":"REWE"}
"""



prompt_zbon = """
    You are an expert invoice parser. Analyze this receipt and return JSON with:
    1) brutto: Notice that brutto may be represented by the name Tagesumsatz; 
    2) netto: Notice that netto may be represented by the name nettoumsatz, and it's near to the attribute Umsatzsteuer and Tagesumsatz;
    3) two confidence scores called score_brutto and score_netto: 
        3.1) if the brutto or netto keyword exists but the result is uncertain, return 0
        3.2) if it is certain, return 1
        3.3) if the keyword doesn't exist, or anything else, return -1
    The final output JSON format should be:
    {
        "brutto": "1234.56",
        "netto": "987.65",
        "score_brutto": 1,
        "score_netto": 0,
    }, or for a receipt without netto:
    {
        "brutto": "15,00",
        "netto": "",
        "score_brutto": 1,
        "score_netto": -1,
    }
"""
prompts_dict = {
    'beleg': {
        "fields":  ["brutto","netto","score_brutto","score_netto","store_name"],
        "prompt": prompt_beleg},
    'zbon': {
        "fields": ["brutto", "netto", "score_brutto", "score_netto"],
        "prompt": prompt_zbon
    }
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
