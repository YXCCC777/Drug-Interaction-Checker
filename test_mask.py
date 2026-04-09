import os
import cv2
import numpy as np

# ==========================================
# 隱私保護（去識別化）模組
# ==========================================
def mask_patient_info(image_path, output_path, mask_ratio=0.25):
    """
    讀取藥單照片，並將頂部包含個資的區域塗黑，達到去識別化效果。
    mask_ratio: 要遮蔽的頂部比例，預設為 25% (0.25)，可依據實際藥單版面調整。
    """
    print("\n[隱私保護模組啟動] 正在對藥單進行去識別化處理...")
    
    # 使用 numpy + cv2.imdecode 來讀取圖片，避免 Windows 系統下中文路徑報錯
    img_data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片：{image_path}")

    height, width, _ = img.shape

    # 計算需要遮蔽的高度
    mask_height = int(height * mask_ratio)

    # 畫一個黑色矩形遮蔽頂部 (起點座標, 終點座標, 顏色 BGR, 填滿 -1)
    cv2.rectangle(img, (0, 0), (width, mask_height), (0, 0, 0), -1)

    # 儲存去識別化後的乾淨圖片
    # 使用 cv2.imencode 寫入，同樣是為了支援中文路徑
    cv2.imencode('.jpg', img)[1].tofile(output_path)
    
    print(f"去識別化完成！安全圖片已儲存為：{output_path}")
    return output_path

# ==========================================
# 單獨測試執行區
# ==========================================
if __name__ == "__main__":
    # 設定資料夾與檔案路徑 (這裡使用我們剛剛討論的標準路徑寫法)
    IMAGE_FOLDER = "test_images"
    raw_image = os.path.join(IMAGE_FOLDER, "sample4.JPG")
    safe_image = os.path.join(IMAGE_FOLDER, "safe_prescription.jpg")
    
    # 檢查防呆：確認資料夾和照片都在
    if not os.path.exists(IMAGE_FOLDER):
        print(f"錯誤：找不到 '{IMAGE_FOLDER}' 資料夾，請確認是否建立！")
    elif not os.path.exists(raw_image):
        print(f"錯誤：找不到原始照片 '{raw_image}'，請確認照片名稱與副檔名大小寫！")
    else:
        try:
            # 💡 測試重點：你可以修改這裡的 mask_ratio 來測試塗黑的範圍
            # 0.25 代表塗黑上面 25%，如果是 0.3 就是 30%
            mask_patient_info(raw_image, safe_image, mask_ratio=0.25)
            
            print("\n✅ 測試成功！請打開 test_images 資料夾，檢查 safe_prescription.jpg 塗黑的位置對不對。")
            
        except Exception as e:
            print(f"發生錯誤: {e}")