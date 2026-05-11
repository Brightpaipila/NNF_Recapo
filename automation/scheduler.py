import schedule
import time
import os

def run_download():
    os.system("python automation/downloader.py")

schedule.every().day.at("06:00").do(run_download)

while True:
    schedule.run_pending()
    time.sleep(60)