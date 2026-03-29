def summarize_all_interactions(interactions_dict):
    """步驟 4：使用自定義固定格式進行總結"""
    print("\n🧠 [Gemini 啟動] 正在依照您的固定格式整理總結清單...")
    
    # 這裡定義你想要的「固定格式」範本
    my_format_template = """
    === 💊 [藥物中文名] ([英文學名]) ===
    * 🛑 【禁忌成分/食物】：(請列出關鍵成分)
    * ⚠️ 【發生什麼事】：(請用一句話白話解釋後果)
    * 💡 【藥師小叮嚀】：(請給一個具體的行動建議)
    -------------------------------------------
    """

    prompt = f"""
    你現在是一位專業的台灣藥師。
    以下是我從美國 FDA 資料庫查到的藥物交互作用原始資料：
    ---
    """
    for drug_tw, raw_interactions in interactions_dict.items():
        prompt += f"【{drug_tw}】\n{raw_interactions}\n\n"
        
    prompt += f"""
    ---
    請幫我根據以上資料進行總結。
    **嚴格遵守以下輸出規則**：
    1. 每一項藥物都必須嚴格遵守這個格式：
    {my_format_template}
    2. 如果某項藥物有多個禁忌成分，請在「禁忌成分」欄位用逗號隔開。
    3. 文字要讓台灣一般大眾（甚至是長輩）都能一眼看懂。
    4. 絕對不要輸出 Markdown 以外的廢話。
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text