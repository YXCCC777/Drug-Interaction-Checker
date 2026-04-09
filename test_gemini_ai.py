import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# 1. 載入環境變數與初始化
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_drugs_from_image(image_path):
    """
    核心功能：使用 Gemini 2.5 Flash 的多模態能力直接讀取圖片並轉為 JSON
    """
    print(f"\n[AI 辨識啟動] 正在分析圖片：{image_path}...")
    
    # 開啟圖片檔案
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"無法開啟圖片檔案: {e}")
        return None

    # 設定 Prompt：這是導引 AI 輸出正確格式的關鍵
    prompt = """
    這是一張台灣醫療院所開立的藥單照片。請仔細觀察圖片中的「藥品名稱與劑量單位」表格區塊。
    
    請幫我擷取表格中的**所有**藥品，並嚴格整理成一個 JSON 清單 (JSON List of Objects)。
    清單中的每個藥品物件需要包含以下欄位：
    {
        "drug_name_tw": "藥品中文或原始名稱（圖片上顯示的名字）",
        "drug_name_en": "藥品英文學名（Generic Name）。請務必將圖片上的藥名轉成 openFDA 查得到的英文學名",
        "frequency": "服用方法（例如：'每日一次'）",
        "quantity": "每次數量（例如：'1'）",
        "days": "天數（例如：'7'）",
        "total_quantity": "總量（例如表格上的 '7' 或 '14'）"
    }
    
    只輸出純 JSON 清單資料，絕對不要包含任何 Markdown 標籤 (例如 ```json ) 或其他解釋。
    """
    
    # 呼叫 Gemini 2.5 Flash
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    try:
        response = model.generate_content(
            [prompt, img],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json", # 強制要求輸出 JSON 格式
                temperature=0.1 # 降低隨機性，確保結果穩定
            )
        )
        
        # 解析 AI 回傳的文字並轉為 Python 字典物件
        return json.loads(response.text)
        
    except json.JSONDecodeError as e:
        print(f"JSON 解析失敗！AI 回傳內容如下：\n{response.text}")
        return None
    except Exception as e:
        print(f"呼叫 API 時發生錯誤: {e}")
        return None

# --- 單獨測試執行區 ---
if __name__ == "__main__":
    # 請確保你的 test_images 資料夾裡有 sample_prescription2.JPG
    IMAGE_PATH = "test_images/sample1.JPG"
    
    if not os.path.exists(IMAGE_PATH):
        print(f"找不到檔案：{IMAGE_PATH}，請檢查路徑與檔名是否正確。")
    else:
        result = extract_drugs_from_image(IMAGE_PATH)
        
        if result:
            print("\n--- 擷取結果 (結構化 JSON) ---")
            # 使用 indent=4 讓印出來的 JSON 比較漂亮易讀
            print(json.dumps(result, indent=4, ensure_ascii=False))
            print("\n-----------------------------")
            print(f"成功擷取到 {len(result)} 項藥品。")