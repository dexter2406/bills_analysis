import requests
import base64

def test_vlm(image_path, model_name="qwen3-vl:4b"):
    # 1. 将图片转为 Base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

    url = "http://localhost:11434/api/chat"
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Analyze this receipt and return JSON with: 1) Brutto and Netto, notice that Netto is smaller than Brutto, and each picture will only contain one unique value for each attribute; 2) the coordinates for one ROI box for highlighting, this ROI should contain the Brutto and Netto area but can be a little bigger for better visualization.",
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
pic_path = "D:\\CodeSpace\\prj_rechnung\\bills_analysis\\outputs\\run1\\preproc\\page_01.preproc.png"
# test_vlm(pic_path)

import cv2
import numpy as np

def draw_normalized_roi(image_path, vlm_coords, output_filename='roi_fixed.jpg'):
    # 1. 读取原图
    img = cv2.imread(image_path)
    if img is None:
        print("Error: 无法读取图片。")
        return
    
    h_orig, w_orig = img.shape[:2]
    print(f"--- 调试信息 ---")
    print(f"原图尺寸: 宽={w_orig}, 高={h_orig}")
    print(f"VLM原始输入(千分位): {vlm_coords}")

    # 2. 定义VLM标准的坐标顺序：[ymin, xmin, ymax, xmax]
    # 注意：这是 Qwen-VL 等大多数模型的标准
    ymin_1k, xmin_1k, ymax_1k, xmax_1k = vlm_coords

    # 3. 核心步骤：反归一化 (De-normalization)
    # 公式：像素坐标 = (千分位坐标 / 1000.0) * 原始尺寸
    # 使用浮点数 / 1000.0 确保计算精度，最后转回整数
    
    # 计算 X 轴 (使用宽度 w_orig)
    xmin_px = int((xmin_1k / 1000.0) * w_orig)
    xmax_px = int((xmax_1k / 1000.0) * w_orig)
    
    # 计算 Y 轴 (使用高度 h_orig)
    ymin_px = int((ymin_1k / 1000.0) * h_orig)
    ymax_px = int((ymax_1k / 1000.0) * h_orig)

    print(f"转换后的像素坐标 (Left, Top, Right, Bottom):")
    print(f"({xmin_px}, {ymin_px}, {xmax_px}, {ymax_px})")
    print("----------------")

    # 4. 边界检查 (防止坐标超出图片范围)
    xmin_px = max(0, xmin_px)
    ymin_px = max(0, ymin_px)
    xmax_px = min(w_orig - 1, xmax_px)
    ymax_px = min(h_orig - 1, ymax_px)

    # 5. 绘制矩形 (OpenCV 需要 左上点 和 右下点)
    # 由于原图很大，线宽设置粗一点 (例如 10) 以便看清
    cv2.rectangle(img, (ymin_px,  xmin_px ), (xmax_px, ymax_px), (0, 0, 255), 10)

    # 6. 保存
    cv2.imwrite(output_filename, img)
    print(f"绘图完成，已保存至: {output_filename}")
    print("请检查生成图片中的红框位置。")

# =========================================
# 替换为你的图片路径
your_image_path = 'outputs\\run1\\preproc\\page_01.preproc.png' 
# =========================================

# VLM 返回的坐标 (假设顺序为 ymin, xmin, ymax, xmax)
# 这是一个又高又窄的框
roi_data = [380, 520, 620, 565] 

draw_normalized_roi(your_image_path, roi_data)