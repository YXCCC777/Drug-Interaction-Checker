from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from .models import MedicationReminder

def check_and_send_reminders():
    # 1. 取得現在的時間（只取到小時和分鐘）
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    print(f"[{datetime.now()}] 鬧鐘巡邏中... 檢查時間: {current_hour:02d}:{current_minute:02d}")

    # 2. 去資料庫找：提醒時間剛好是現在的藥物
    # 注意：這裡假設你的模型欄位叫 remind_time
    reminders = MedicationReminder.objects.filter(
        remind_time__hour=current_hour,
        remind_time__minute=current_minute
    )

    for r in reminders:
        # 這裡就是未來要放 Firebase 推播程式碼的地方
        print(f"！！！時間到了！！！ 準備推播給用戶。 藥物名稱：{r.drug_name}")

def start():
    # 建立一個背景執行的排程器
    scheduler = BackgroundScheduler()
    # 設定每 1 分鐘執行一次巡邏任務
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1)
    scheduler.start()