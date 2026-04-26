from django.apps import AppConfig

class DrugRemindersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'drug_reminders'

    def ready(self):
        # 當 Django 準備好後，啟動我們剛剛寫的 updater
        from . import updater
        updater.start()