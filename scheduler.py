
from apscheduler.schedulers.blocking import BlockingScheduler
from utils.batch_runner import run_batch_from_config

def scheduled_batch_job():
    print("🕐 Scheduled batch job starting...")
    run_batch_from_config()

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_batch_job, "interval", hours=6)  # Every 6 hours
    print("📅 Scheduler started — running every 6 hours.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Scheduler stopped.")
