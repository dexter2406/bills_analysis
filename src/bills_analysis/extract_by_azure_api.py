# src/bills_analysis/azure_extraction.py

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

load_dotenv()

def analyze_document_with_azure(image_path: str, model_id: str = "prebuilt-invoice"):
    """
    通用分析函数：支持指定使用 invoice 或 receipt 模型
    提取：brutto, netto, store_name, date + 对应 confidence
    如果是 invoice 模型提取，则额外提取 invoice_id
    """
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    print(f"[Azure] model_id={model_id}")   # "prebuilt-invoice" / "prebuilt-receipt"
    print(f"[Azure] image_path={image_path}")
    # print(f"[Azure] endpoint_set={bool(endpoint)} key_set={bool(key)}")

    if not endpoint or not key:
        raise ValueError("请在环境变量中设置 AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT 和 KEY")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
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
    print(f"[Azure] Finished documents_count={len(result.documents) if result.documents else 0}")

    extracted_data = {
        "model_used": model_id,
        "store_name": None,
        "confidence_store_name": None,
        "brutto": None,
        "confidence_brutto": None,
        "netto": None,
        "confidence_netto": None,
        "date": None,
        "confidence_date": None,
        "invoice_id": None
    }

    if result.documents:
        doc = result.documents[0]
        fields = doc.fields
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
        # Receipt 对应 Total; Invoice 对应 InvoiceTotal
        f_total = fields.get("Total") if model_id == "prebuilt-receipt" else fields.get("InvoiceTotal")
        if f_total:
            # 优先取金额数值，若无则取数字数值
            extracted_data["brutto"] = f_total.value_currency.amount if f_total.value_currency else f_total.value_number
            extracted_data["confidence_brutto"] = f_total.confidence
        print(f"[Azure] brutto={extracted_data['brutto']} conf={extracted_data['confidence_brutto']}")

        # 3. Netto (净额) 提取
        # 官方文档显示两者均对应 Subtotal 字段
        f_subtotal = fields.get("Subtotal")
        if f_subtotal:
            extracted_data["netto"] = f_subtotal.value_currency.amount if f_subtotal.value_currency else f_subtotal.value_number
            extracted_data["confidence_netto"] = f_subtotal.confidence
            print(f"[Azure] subtotal={extracted_data['netto']} conf={extracted_data['confidence_netto']}")

        # 4. 用 TotalTax 兜底推断 brutto 或 netto（避免使用 TaxRate）
        if extracted_data["brutto"] is None or extracted_data["netto"] is None:
            f_total_tax = fields.get("TotalTax")
            total_tax = None
            if f_total_tax:
                total_tax = f_total_tax.value_currency.amount if f_total_tax.value_currency else f_total_tax.value_number
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

        # 5. Invoice ID (仅限 Invoice 模型)
        if model_id == "prebuilt-invoice":
            f_inv_id = fields.get("InvoiceId")
            extracted_data["invoice_id"] = f_inv_id.value_string if f_inv_id else None

        # 6. Date (invoice -> InvoiceDate, receipt -> TransactionDate)
        if model_id == "prebuilt-receipt":
            f_date = fields.get("TransactionDate")
        else:
            f_date = fields.get("InvoiceDate")
        if f_date:
            extracted_data["date"] = f_date.value_date if hasattr(f_date, "value_date") else None
            extracted_data["confidence_date"] = f_date.confidence
    print(f"[Azure] extracted_data for this page:\n{extracted_data}")
    return extracted_data

if __name__ == "__main__":  

    img_path = rf"D:\CodeSpace\prj_rechnung\bills_analysis\data\samples\scanned\bad_case\Nanjing 20_23.pdf"
    analyze_document_with_azure(img_path, model_id="prebuilt-invoice")
    img_path = rf"D:\CodeSpace\prj_rechnung\bills_analysis\data\samples\scanned\Metzgerei 105_13.pdf"
    analyze_document_with_azure(img_path, model_id="prebuilt-receipt")
