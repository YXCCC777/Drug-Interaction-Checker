from django.shortcuts import render
from django.http import JsonResponse
from .models import MedicationReminder  # 引入你寫的資料模型

# 建立一個視圖 (View) 來接收設定
def add_reminder_api(request):
    if request.method == "POST":
        # 從前端（例如 LINE Bot 或 網頁）拿到的資料
        name = request.POST.get('drug_name')
        time = request.POST.get('remind_time')
        
        # 存入資料庫
        new_item = MedicationReminder.objects.create(
            drug_name=name, 
            remind_time=time
        )
        
        return JsonResponse({"message": f"成功設定 {name} 的提醒！", "id": new_item.id})
    
    return JsonResponse({"error": "請使用 POST 方法傳送資料"}, status=400)