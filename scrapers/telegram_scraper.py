
import asyncio

async def scrape_telegram(query: str, search_type: str):
    # Simulated delay for Telegram search
    await asyncio.sleep(2)
    return {
        "platform": "Telegram",
        "query": query,
        "search_type": search_type,
        "results": [
            f"Simulated Telegram post about '{query}'",
            f"Another message matching '{query}'"
        ],
        "html": "<div>Simulated Telegram HTML</div>",
        "screenshot": "/static/screenshots/telegram_sample.png"
    }
