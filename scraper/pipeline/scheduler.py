# pipeline/scheduler.py
import schedule
import time
from pipeline.run_scraper import run

def job():
    print(f"[SCHEDULE] Menjalankan scraper...")
    run(debug=False)

schedule.every(6).hours.do(job)

if __name__ == "__main__":
    print("[SCHEDULE] Scheduler aktif, scraping tiap 6 jam. Ctrl+C untuk stop.")
    job()  # jalankan sekali langsung saat start
    while True:
        schedule.run_pending()
        time.sleep(60)