import os
import json
import requests
from dotenv import load_dotenv
from google.cloud import vision
import google.generativeai as genai

# 載入環境變數
load_dotenv()

# 初始化 Google Gemini API 客戶端
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_text_with_vision(image_path):
    """步驟 1: 使用 Google Vision API 進行 OCR 辨識"""
    print("啟動 Google Vision OCR 掃描...")
    vision_client = vision.ImageAnnotatorClient()
    
    with open(image_path, "rb") as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    
    if response.error.message:
        raise Exception(f"{response.error.message}")
        
    return texts[0].description if texts else ""

def structure_text_with_llm(raw_text):
    """步驟 2: 使用 Google Gemini 將 OCR 文字結構化，並翻譯成英文學名"""
    print("啟動 Gemini 解析藥單資訊...")
    
    # 提示詞 (Prompt) 設計：明確告知需要的 JSON 格式
   # 提示詞 (Prompt) 設計：明確告知需要的 JSON 格式，並封殺 List
    prompt = f"""
    以下是從藥單上掃描下來的原始文字：
    {raw_text}
    
    請幫我擷取「第一項」藥物資訊即可，並嚴格以單一 JSON Object (字典) 格式輸出，絕對不要使用陣列 (List/Array) 也就是 [ ] 包覆：
    {{
        "drug_name_en": "藥品英文學名 (Generic Name)。請務必將台灣藥名轉成 openFDA 查得到的英文學名，例如把 '普拿疼' 轉為 'acetaminophen'。",
        "frequency": "服藥頻率 (如：一天三次)",
        "quantity": "數量 (如：30顆)"
    }}
    
    只輸出 JSON，不要有其他廢話或 Markdown 標籤。
    """
    
    # 使用 Gemini 1.5 Flash 模型 (速度快、免費額度夠，非常適合專題 Demo)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # 強制 Gemini 直接輸出 JSON 格式 (response_mime_type)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1 # 降低隨機性，確保每次輸出的格式都很穩定
        )
    )
    
    result = response.text
    return json.loads(result)

def query_openfda_interactions(drug_name_en):
    """步驟 3: 將藥名丟給 openFDA 查詢交互作用資訊"""
    print(f"啟動 openFDA 查詢：{drug_name_en} 的交互作用...")
    
    # 使用 openFDA 的 drug label API 查詢
    url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:\"{drug_name_en}\"&limit=1"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        try:
            # 嘗試擷取藥物交互作用欄位 (drug_interactions)
            interactions = data["results"][0]["drug_interactions"][0]
            return interactions
        except KeyError:
            return "查無具體的藥物交互作用說明欄位。"
    else:
        return "openFDA 找不到此藥物或 API 呼叫失敗。"

# --- 主程式執行區 ---
if __name__ == "__main__":
    # 請先在資料夾中放一張測試用的藥單照片
    test_image = "sample_prescription.JPG" 
    
    if not os.path.exists(test_image):
        print(f"請準備一張名為 {test_image} 的照片放在同一個資料夾下！")
    else:
        try:
            # 1. OCR 辨識
            raw_text = extract_text_with_vision(test_image)
            print("\n--- OCR 原始文字 ---")
            print(raw_text)
            
            # 2. LLM 結構化
            structured_data = structure_text_with_llm(raw_text)
            print("\n--- Gemini 結構化資料 ---")
            print(json.dumps(structured_data, indent=4, ensure_ascii=False))
            
            # 3. openFDA 查詢
            drug_en = structured_data.get("drug_name_en", "")
            if drug_en:
                interactions_info = query_openfda_interactions(drug_en)
                print("\n--- openFDA 交互作用警告 ---")
                print(interactions_info)
                
        except Exception as e:
            print(f"發生錯誤: {e}")