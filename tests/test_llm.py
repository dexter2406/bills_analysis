import base64
from pathlib import Path

import cv2
import requests

def _resize_to_width(path: Path, target_width: int = 1000) -> bytes:
    """等比例缩放到指定宽度，返回PNG字节，用于减少VLM负载。"""
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {path}")
    h, w = img.shape[:2]
    if w <= target_width:
        # 宽度已满足，直接返回原图
        _, buf = cv2.imencode(".png", img)
        return buf.tobytes()
    scale = target_width / w
    resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, buf = cv2.imencode(".png", resized)
    return buf.tobytes()


def test_vlm(image_path, prompt, model_name="qwen3-vl:4b"):
    # 1. 缩放并转为 Base64
    img_bytes = _resize_to_width(Path(image_path), target_width=1000)
    base64_image = base64.b64encode(img_bytes).decode("utf-8")

    url = "http://localhost:11434/api/chat"
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64_image]
            }
        ],
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        # 如果返回 400，这里会打印出详细的错误信息
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
        else:
            print(response.json()['message']['content'])
    except Exception as e:
        print(f"Request failed: {e}")


# 运行测试
prompt_beleg = """
    You are an expert invoice parser. Analyze this receipt and return JSON with: 
    1) Brutto and Netto. Notice that Brutto may be represented by the name Tagesumsatz; 
    2) two confidence scores called score_brutto and score_netto, if the keyword doesn't exist, return -1, if it exists but the result is uncertain, return 0, if it is certain, return 1;
    3) the store name, usually at the top of the receipt.
    The final output JSON format should be:
    {
        "Brutto": "8,94",
        "Netto": "8,36",
        "score_brutto": 1,
        "score_netto": 1,
        "store_name": "REWE"
    }
"""
prompt_zbon = """
    You are an expert invoice parser. Analyze this receipt and return JSON with:
    1) Brutto: Notice that Brutto may be represented by the name Tagesumsatz; 
    2) Netto: Notice that Netto may be represented by the name Nettoumsatz, and it's near to the attribute Umsatzsteuer and Tagesumsatz;
    3) two confidence scores called score_brutto and score_netto, if the keyword doesn't exist, return -1, if it exists but the result is uncertain, return 0, if it is certain, return 1;
    The final output JSON format should be:
    {
        "Brutto": "1234.56",
        "Netto": "987.65",
        "score_brutto": 1,
        "score_netto": 0,
    }
"""

pic_path = rf"outputs\run1\preproc\page_01.preproc.png"
test_vlm(pic_path, prompt_beleg)

pic_path = rf"D:\CodeSpace\prj_rechnung\rsc\2510DO Z-Bon\2510DO Z-Bon\pngs\06_10_2025 do\preproc\page_01.preproc.png"
test_vlm(pic_path, prompt_zbon)
