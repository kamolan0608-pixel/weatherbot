import asyncio
import requests
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
import os
from dotenv import load_dotenv



# ========== SOZLAMALAR ==========
load_dotenv()  # .env fayldan ma'lumotlarni yuklaydi
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OWM_API_KEY = os.getenv("OWM_API_KEY")
CITY_NAME = os.getenv("CITY_NAME", "Bekobod,UZ")
TIMEZONE = pytz.timezone("Asia/Tashkent")  # ⚠️ MUHIM: pytz obyekt
UNITS = "metric"
LANG = "uz"
# ================================

bot = Bot(token=TELEGRAM_TOKEN)


def get_weather(city_name: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": OWM_API_KEY,
        "units": UNITS,
        "lang": LANG,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def format_weather_message(data: dict):
    name = data.get("name")
    weather = data["weather"][0]["description"].capitalize()
    temp = data["main"]["temp"]
    feels = data["main"].get("feels_like")
    humidity = data["main"].get("humidity")
    wind = data.get("wind", {}).get("speed")
    sunrise_ts = data.get("sys", {}).get("sunrise")
    sunset_ts = data.get("sys", {}).get("sunset")

    tz = TIMEZONE
    def ts_to_local(ts):
        if not ts:
            return "—"
        return datetime.fromtimestamp(ts, tz).strftime("%H:%M")

    sunrise = ts_to_local(sunrise_ts)
    sunset = ts_to_local(sunset_ts)
    degree_sign = "°C" if UNITS == "metric" else "°F"

    msg = (
        f"☁️ Ob-havo: *{name}*\n\n"
        f"🔹 Holat: {weather}\n"
        f"🌡 Havo: {temp}{degree_sign} (Tuyulishi: {feels}{degree_sign})\n"
        f"💧 Namlik: {humidity}%\n"
        f"🌬 Shamol: {wind} m/s\n"
        f"🌅 Quyosh chiqishi: {sunrise}\n"
        f"🌇 Quyosh botishi: {sunset}\n\n"
        f"_Vaqt zonasi: Asia/Tashkent_"
    )
    return msg


async def send_weather():
    try:
        data = get_weather(CITY_NAME)
        text = format_weather_message(data)
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
        print(f"[{datetime.now()}] ✅ Ob-havo yuborildi.")
    except Exception as e:
        print("❌ Xatolik:", e)


async def main():
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    times = [(21, 53), (20, 40), (20, 41)]
    for hour, minute in times:
        trigger = CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE)
        scheduler.add_job(send_weather, trigger=trigger, id=f"weather_{hour}_{minute}")
    scheduler.start()

    print("Scheduler ishga tushdi. Quyidagi vaqtlarda xabar yuboriladi:")
    for hour, minute in times:
        print(f" - {hour:02d}:{minute:02d}")
    # Hozir test uchun bir marta yuborishni istasangiz — quyidagini yoqing:
    # await send_weather()

    # Botni fon rejimida ushlab turish
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
