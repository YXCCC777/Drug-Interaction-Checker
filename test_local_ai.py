import os
import ollama
from PIL import Image

def test_lightweight_vision(image_path):
    print("\n[1/2] 正在幫照片瘦身 (避免記憶體爆炸)...")
    try:
        img = Image.open(image_path)
        # 將照片按比例縮小到最長邊不超過 800 像素
        img.thumbnail((800, 800)) 
        temp_path = "test_images/temp_resized.jpg"
        img.save(temp_path)
        print(f"照片已縮小並暫存為 {temp_path}")
    except Exception as e:
        print(f"處理照片失敗: {e}")
        return

    print("\n[2/2] 🧠 啟動 Moondream 極輕量視覺大腦...")
    
    # 給予最簡單直接的指令，不逼它轉 JSON，先看它到底看不看得到！
    prompt = "這是一張藥單。請幫我列出圖片中所有的「藥品名稱」和「數量」。"
    
    try:
        response = ollama.chat(
            model='moondream', 
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [temp_path] # 傳送縮小後的照片
            }]
        )
        
        print("\n🎉 [最終結果] Moondream 看到的內容：")
        print(response['message']['content'])
        
    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    IMAGE_PATH = "test_images/sample1.jpg" 
    
    if not os.path.exists(IMAGE_PATH):
        print(f"找不到檔案：{IMAGE_PATH}")
    else:
        test_lightweight_vision(IMAGE_PATH)