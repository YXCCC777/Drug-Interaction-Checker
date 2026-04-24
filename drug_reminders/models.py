from django.db import models

class MedicationReminder(models.Model):
    # 藥品名稱 (可以從組員辨識出的 drugs_list 傳過來)
    drug_name = models.CharField(max_length=200)
    # 提醒的時間
    remind_time = models.TimeField()
    # 是否開啟提醒
    is_active = models.BooleanField(default=True)
    # 建立時間
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.drug_name} - {self.remind_time}"
