import asyncio
import requests
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
import os
from dotenv import load_dotenv
from flask import Flask
import threading

app = Flask("bot")
@app.route("/")
def home():
    return "WeatherBot is alive!"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()
# ========== SOZLAMALAR ==========
load_dotenv()  # .env fayldan ma'lumotlarni yuklaydi
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWM_API_KEY = os.getenv("OWM_API_KEY")
CITY_NAME = os.getenv("CITY_NAME", "Bekobod,UZ")
TIMEZONE = pytz.timezone("Asia/Tashkent")  # ⚠️ MUHIM: pytz obyekt
UNITS = "metric"
LANG = "uz"

# 🔹 Bir nechta chat ID larni .env orqali olish
CHAT_IDS = os.getenv("CHAT_IDS", "")
# Masalan .env faylda: CHAT_IDS=-1001234567890,-1009876543210,123456789
CHAT_IDS = [int(x.strip()) for x in CHAT_IDS.split(",") if x.strip()]

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
    # === Sana va joy ===
    now = datetime.now(TIMEZONE)
    sana = now.strftime("%d-%B %Y")  # masalan: 15-Oktyabr 2025
    sana = sana.replace("January", "Yanvar").replace("February", "Fevral").replace("March", "Mart") \
               .replace("April", "Aprel").replace("May", "May").replace("June", "Iyun") \
               .replace("July", "Iyul").replace("August", "Avgust").replace("September", "Sentabr") \
               .replace("October", "Oktabr").replace("November", "Noyabr").replace("December", "Dekabr")

    name = data.get("name")

    # === Ob-havo holati (tarjima) ===
    weather_en = data["weather"][0]["main"].lower()
    weather_map = {
        "clear": "ochiq osmon",
        "clouds": "bulutli",
        "rain": "yomgʻir",
        "drizzle": "mayda yomgʻir",
        "thunderstorm": "momaqaldiroq",
        "snow": "qor yogʻmoqda",
        "mist": "tuman",
        "fog": "tuman",
        "haze": "tutunli",
        "smoke": "tutun",
        "dust": "changli havo",
        "sand": "qumli havo",
        "ash": "kul bosgan havo",
        "squall": "shamol kuchaygan",
        "tornado": "bo‘ron"
    }
    weather = weather_map.get(weather_en, data["weather"][0]["description"].capitalize())

    # === Asosiy ma’lumotlar ===
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

    # === Yakuniy xabar ===
    msg = (
        f"📅 *{sana}* kuni *{name}* shahrida kutilayotgan ob-havo maʼlumoti:\n\n"
        f"🔹 Holat: {weather}\n"
        f"🌡 Harorat: {temp}{degree_sign} (Tuyulishi: {feels}{degree_sign})\n"
        f"💧 Namlik: {humidity}%\n"
        f"🌬 Shamol tezligi: {wind} m/s\n"
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
    times = [(11, 20), (11, 25), (11, 30)]
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
