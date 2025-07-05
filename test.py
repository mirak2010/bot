from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
import asyncio

async def test_job():
    print("Scheduler is working!")

async def main():
    scheduler = AsyncIOScheduler(timezone=timezone('Asia/Tashkent'))
    scheduler.add_job(test_job, 'interval', seconds=5)
    scheduler.start()

    # Keep the loop running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
