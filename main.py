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
import random

# === Flask Web Server (Render.com uptime uchun) ===
app = Flask("bot")

@app.route("/")
def home():
    return "WeatherBot is alive!"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()

# === .env dan sozlamalar ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWM_API_KEY = os.getenv("OWM_API_KEY")
CITY_NAME = os.getenv("CITY_NAME", "Bekobod,UZ")

# ✅ Bir nechta chat ID (vergul bilan yoziladi)
# Masalan: CHAT_IDS=-10012345,-10067890,123456789
CHAT_IDS = [x.strip() for x in os.getenv("CHAT_IDS", "").split(",") if x.strip()]

TIMEZONE = pytz.timezone("Asia/Tashkent")
UNITS = "metric"
LANG = "uz"

bot = Bot(token=TELEGRAM_TOKEN)

# === Ob-havo olish funksiyasi ===
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


def get_greeting(now):
    hour = now.hour
    if 5 <= hour < 11:
        return "🌅 *Xayrli tong!* Yangi kun boshlandi ☀️"
    elif 11 <= hour < 18:
        return "🌤 *Xayrli kun!* 🌞"
    else:
        return "🌙 *Xayrli oqshom!* 🌌"


# === Xabar formatlash funksiyasi ===
def format_weather_message(data: dict):
    now = datetime.now(TIMEZONE)
    sana = now.strftime("%d-%B %Y")
    sana = sana.replace("January", "Yanvar").replace("February", "Fevral").replace("March", "Mart") \
               .replace("April", "Aprel").replace("May", "May").replace("June", "Iyun") \
               .replace("July", "Iyul").replace("August", "Avgust").replace("September", "Sentabr") \
               .replace("October", "Oktabr").replace("November", "Noyabr").replace("December", "Dekabr")

    soat = now.strftime("%H:%M")
    
    name = data.get("name")
    weather_en = data["weather"][0]["main"].lower()
    weather_map = {
        "clear": "ochiq osmon",
        "clouds": "bulutli",
        "rain": "yomgʻir",
        "drizzle": "mayda yomgʻir",
        "thunderstorm": "momaqaldiroq",
        "snow": "qor",
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

    temp = round(data["main"]["temp"])
    feels = round(data["main"].get("feels_like"))
    humidity = data["main"].get("humidity")
    wind = round(data.get("wind", {}).get("speed", 0), 1)
    sunrise_ts = data.get("sys", {}).get("sunrise")
    sunset_ts = data.get("sys", {}).get("sunset")

    tz = TIMEZONE
    def ts_to_local(ts):
        return datetime.fromtimestamp(ts, tz).strftime("%H:%M") if ts else "—"

    sunrise = ts_to_local(sunrise_ts)
    sunset = ts_to_local(sunset_ts)
    degree_sign = "°C"

    greeting = get_greeting(now)
    
    msg = (
        f"{greeting}\n\n"
        f"📍 *{name}* shahrining ob-havo ma'lumotlari ({sana}, soat {soat})\n\n"
        f"🔸 Havo holati: *{weather}*\n"
        f"🌡 Harorat: *{temp}{degree_sign}* (Tuyulishi: {feels}{degree_sign})\n"
        f"💧 Namlik: {humidity}%\n"
        f"🌬 Shamol: {wind} m/s\n"
        f"🌅 Quyosh chiqishi: {sunrise}\n"
        f"🌇 Quyosh botishi: {sunset}\n\n"
        f"🕒 *Tashkent vaqti bo‘yicha ma’lumot*"
    )
    return msg


# === Xabar yuborish (rasm bilan, bir nechta chatga) ===
async def send_weather():
    try:
        data = get_weather(CITY_NAME)
        text = format_weather_message(data)

        now = datetime.now(TIMEZONE)
        hour = now.hour
        weather_en = data["weather"][0]["main"].lower()

        # === Kun vaqtini aniqlash ===
        if 5 <= hour < 11:
            time_period = "morning"
        elif 11 <= hour < 18:
            time_period = "day"
        else:
            time_period = "evening"

        # === Rasm variantlari ===
        image_map = {
            "clear": [f"images/{time_period}_clear1.jpg", f"images/{time_period}_clear2.jpg"],
            "clouds": [f"images/{time_period}_clouds1.jpg", f"images/{time_period}_clouds2.jpg"],
            "rain": [f"images/{time_period}_rain1.jpg", f"images/{time_period}_rain2.jpg"],
            "drizzle": [f"images/{time_period}_rain1.jpg", f"images/{time_period}_rain2.jpg"],
            "thunderstorm": [f"images/{time_period}_storm1.jpg"],
            "snow": [f"images/{time_period}_snow1.jpg"],
            "mist": [f"images/{time_period}_fog1.jpg", f"images/{time_period}_fog2.jpg"],
            "fog": [f"images/{time_period}_fog1.jpg", f"images/{time_period}_fog2.jpg"],
            "haze": [f"images/{time_period}_fog1.jpg"],
            "smoke": [f"images/{time_period}_fog1.jpg"]
        }

        # Default rasm
        image_list = image_map.get(weather_en, [f"images/{time_period}_default1.jpg", "images/default.jpg"])
        image_path = random.choice(image_list)
        if not os.path.exists(image_path):
            image_path = "images/default.jpg"

        # === Har bir chatga yuborish ===
        for chat_id in CHAT_IDS:
            try:
                with open(image_path, "rb") as photo:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text,
                        parse_mode="Markdown"
                    )
                print(f"✅ {chat_id} ga yuborildi ({time_period}, {weather_en}, {os.path.basename(image_path)})")
            except Exception as e:
                print(f"⚠️ {chat_id} ga yuborishda xato: {e}")

    except Exception as e:
        print("❌ Umumiy xatolik:", e)


# === Rejalashtirish (scheduler) ===
async def main():
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Xabar yuboriladigan vaqtlar
    times = [(1, 39), (1, 41)]  # soat 08:00 va 20:00 da
    for hour, minute in times:
        trigger = CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE)
        scheduler.add_job(send_weather, trigger=trigger)

    scheduler.start()
    print("✅ Scheduler ishga tushdi. Quyidagi vaqtlarda xabar yuboriladi:")
    for hour, minute in times:
        print(f" - {hour:02d}:{minute:02d}")

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
