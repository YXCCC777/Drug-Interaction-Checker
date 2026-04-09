import os
import cv2
import numpy as np
import easyocr

def ocr_keyword_mask(image_path, output_path):
    print("\n[智慧遮蔽啟動] 正在載入 EasyOCR 模型...")
    reader = easyocr.Reader(['ch_tra', 'en'])
    print(f"正在讀取並分析圖片：{image_path} ...")
    
    img_data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片：{image_path}")

    # ==========================================
    # 🌟 新增：影像預處理 (幫 OCR 戴眼鏡)
    # ==========================================
    print(" 正在進行影像增強處理...")
    
    # 1. 轉成灰階 (去除粉紅色色塊的干擾)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 拉高對比度 (讓黑字更黑，白紙更白)
    # alpha 是對比度 (1.0~3.0)，beta 是亮度增加值
    alpha = 1.8 
    beta = 30   
    enhanced_img = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
    
    # (可選) 你可以把增強後的圖片存下來看看長怎樣，方便你除錯
    # cv2.imwrite("test_images/debug_enhanced.jpg", enhanced_img)
    
    # ==========================================
    
    img_height, img_width, _ = img.shape
    
    # 💡 注意這裡：我們把「增強後」的 enhanced_img 交給 reader 去讀！
    # 同時開啟 EasyOCR 內建的對比度調整參數
    results = reader.readtext(enhanced_img, adjust_contrast=0.5)
    print("--- AI 到底看到了什麼？ ---")
    for _, text, _ in results:
        print(text)
    print("---------------------------")
    
    sensitive_keywords = ['姓名', '生日', '年齡', '證號', '身份證', '醫師姓名']
    mask_count = 0

    for result in results:
        if len(result) != 3:
            continue
            
        bbox, text, prob = result
        
        # 因為照片畫質較差，我們可以把過濾標準稍微調低一點 (例如從 0.4 降到 0.25)
        if prob < 0.25:
            continue

        if any(keyword in text for keyword in sensitive_keywords):
            if isinstance(bbox, list) and len(bbox) == 4:
                print(f" ⚠️ 偵測到敏感資訊：[{text}] (信心度: {prob:.2f})")
                
                top_left = bbox[0]
                bottom_right = bbox[2]
                
                x1, y1 = int(top_left[0]), int(top_left[1])
                x2, y2 = int(bottom_right[0]), int(bottom_right[2])
                
                # 向右延伸遮蔽真正的個資 (可以依據這張照片的排版調大一點，比如 400)
                extend_x = min(x2 + 400, img_width) 
                
                y1 = max(y1 - 15, 0)
                y2 = min(y2 + 15, img_height)

                # 💡 注意：畫黑框還是畫在「原始的彩色圖片 img」上，這樣最後存檔才會是彩色的
                cv2.rectangle(img, (x1, y1), (extend_x, y2), (0, 0, 0), -1)
                mask_count += 1

    cv2.imencode('.jpg', img)[1].tofile(output_path)
    
    print(f"\n✅ 掃描完畢！共塗黑了 {mask_count} 處敏感區域。")
    print(f"安全圖片已儲存為：{output_path}")
    return output_path

if __name__ == "__main__":
    IMAGE_FOLDER = "test_images"
    raw_image = os.path.join(IMAGE_FOLDER, "sample1.jpg") # 換成這張照片的名字
    safe_image = os.path.join(IMAGE_FOLDER, "ocr_safe_prescription.jpg")
    
    if not os.path.exists(IMAGE_FOLDER):
        print(f"錯誤：找不到 '{IMAGE_FOLDER}' 資料夾！")
    elif not os.path.exists(raw_image):
        print(f"錯誤：找不到原始照片 '{raw_image}'！")
    else:
        try:
            ocr_keyword_mask(raw_image, safe_image)
        except Exception as e:
            print(f"發生錯誤: {e}")
