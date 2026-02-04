# src/bills_analysis/azure_extraction.py

import json
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest


def _extract_amount(field) -> float | None:
    print([f"Extracting amount from field: {field}"])
    if not field:
        return None
    if getattr(field, "value_currency", None):
        print([f"  found value_currency: {field.value_currency}"])
        return field.value_currency.amount
    if getattr(field, "valueCurrency", None):
        print([f"  found valueCurrency: {field.valueCurrency}"])
        return field.valueCurrency.amount
    if getattr(field, "value_number", None) is not None:
        print([f"  found value_number: {field.value_number}"])  
        return field.value_number
    # Fallback: parse content like "1.181,75"
    content = getattr(field, "content", None)
    if not content:
        return None
    text = str(content).strip()
    if not text:
        return None
    text = text.replace(" ", "")
    # normalize 1.181,75 or 1,181.75
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None

load_dotenv()

def analyze_document_with_azure(image_path: str, model_id: str = "prebuilt-invoice"):
    """
    通用分析函数：支持指定使用 invoice 或 receipt 模型
    提取：brutto, netto, store_name, total_tax, run_date + 对应 confidence
    如果是 invoice 模型提取，则额外提取 invoice_id
    """
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    print(f"[Azure] model_id={model_id}")   # "prebuilt-invoice" / "prebuilt-receipt"
    print(f"[Azure] image_path={image_path}")
    # print(f"[Azure] endpoint_set={bool(endpoint)} key_set={bool(key)}")

    if not endpoint or not key:
        raise ValueError("请在环境变量中设置 AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT 和 KEY")

    client = DocumentIntelligenceClient(
        endpoint=endpoint, 
        credential=AzureKeyCredential(key),
        api_version="2024-11-30"
        )
    print("[Azure] client created")

    # 读取本地文件为字节流
    with open(image_path, "rb") as f:
        file_content = f.read()
    print(f"[Azure] bytes_read={len(file_content)}")

    # 根据调用前判断好的 model_id 进行分析
    # print("[Azure] begin analyze")
    poller = client.begin_analyze_document(
        model_id, 
        AnalyzeDocumentRequest(bytes_source=file_content)
    )
    result = poller.result()
    print(json.dumps(result.as_dict(), indent=2))
    print(f"[Azure] Finished documents_count={len(result.documents) if result.documents else 0}")

    extracted_data = {
        "model_used": model_id,
        "store_name": None,
        "confidence_store_name": None,
        "brutto": None,
        "confidence_brutto": None,
        "total_tax": None,
        "confidence_total_tax": None,
        "netto": None,
        "confidence_netto": None,
        "invoice_id": None
    }

    if result.documents:
        doc = result.documents[0]
        fields = doc.fields
        # print(fields)
        print(f"[Azure] fields keys: {list(fields.keys())}")
        # 1. Store Name 提取
        if model_id == "prebuilt-receipt":
            f_merchant = fields.get("MerchantName")
            extracted_data["store_name"] = f_merchant.value_string if f_merchant else None
            extracted_data["confidence_store_name"] = f_merchant.confidence if f_merchant else None
        else: # prebuilt-invoice
            f_vendor = fields.get("VendorName")
            extracted_data["store_name"] = f_vendor.value_string if f_vendor else None
            extracted_data["confidence_store_name"] = f_vendor.confidence if f_vendor else None

        # 2. Brutto (总额) 提取
        # Prefer model-specific field, but fallback to other common fields.
        f_total = None
        if model_id == "prebuilt-receipt":
            f_total = fields.get("Total") or fields.get("InvoiceTotal")
        else:
            f_total = fields.get("InvoiceTotal") or fields.get("Total")
        print(f"[Azure] f_total field: {f_total}")
        if f_total:
            extracted_data["brutto"] = _extract_amount(f_total)
            extracted_data["confidence_brutto"] = f_total.confidence
        print(f"[Azure] brutto={extracted_data['brutto']} conf={extracted_data['confidence_brutto']}")

        # 3. Netto (净额) 提取
        # 官方文档显示两者均对应 Subtotal 字段
        f_subtotal = fields.get("Subtotal")
        if f_subtotal:
            extracted_data["netto"] = _extract_amount(f_subtotal)
            extracted_data["confidence_netto"] = f_subtotal.confidence
            print(f"[Azure] subtotal={extracted_data['netto']} conf={extracted_data['confidence_netto']}")

        # 4. TotalTax 提取（同时作为 brutto/netto 兜底）
        if extracted_data["brutto"] is None or extracted_data["netto"] is None:
            f_total_tax = fields.get("TotalTax")
            total_tax = None
            if f_total_tax:
                total_tax = _extract_amount(f_total_tax)
                extracted_data["total_tax"] = total_tax
                extracted_data["confidence_total_tax"] = f_total_tax.confidence
            if total_tax is not None:
                print(f"[Azure] TotalTax={total_tax} used for fallback")
                if extracted_data["brutto"] is None and extracted_data["netto"] is not None:
                    extracted_data["brutto"] = round(extracted_data["netto"] + total_tax, 2)
                    extracted_data["confidence_brutto"] = -1
                elif extracted_data["netto"] is None and extracted_data["brutto"] is not None:
                    extracted_data["netto"] = round(extracted_data["brutto"] - total_tax, 2)
                    extracted_data["confidence_netto"] = -1
            else:
                print("[Azure] TotalTax missing; cannot infer brutto/netto")
        else:
            f_total_tax = fields.get("TotalTax")
            if f_total_tax:
                extracted_data["total_tax"] = (
                    f_total_tax.value_currency.amount
                    if f_total_tax.value_currency
                    else f_total_tax.value_number
                )
                extracted_data["confidence_total_tax"] = f_total_tax.confidence

        # 5. Invoice ID (仅限 Invoice 模型)
        if model_id == "prebuilt-invoice":
            f_inv_id = fields.get("InvoiceId")
            extracted_data["invoice_id"] = f_inv_id.value_string if f_inv_id else None

    print(f"[Azure] extracted_data for this page:\n{extracted_data}")
    return extracted_data

if __name__ == "__main__":  

    img_path = rf"D:\CodeSpace\prj_rechnung\bills_analysis\data\samples\scanned\bad_case\Nanjing 20_23.pdf"
    analyze_document_with_azure(img_path, model_id="prebuilt-invoice")
    # img_path = rf"D:\CodeSpace\prj_rechnung\bills_analysis\data\samples\scanned\Metzgerei 105_13.pdf"
    # analyze_document_with_azure(img_path, model_id="prebuilt-receipt")
