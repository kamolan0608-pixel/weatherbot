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
CHAT_ID = int(os.getenv("CHAT_ID"))  # faqat bitta ID
OWM_API_KEY = os.getenv("OWM_API_KEY")
CITY_NAME = os.getenv("CITY_NAME", "Bekobod,UZ")

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
        return (
            "🌅 *Xayrli tong!*\n"
            "Yangi kun boshlandi. Sizga unumli ishlar va iliq kayfiyat tilaymiz."
        )
    elif 11 <= hour < 18:
        return (
            "🌤 *Xayrli kun!* 🌞\n"
        )
    else:
        return (
            "🌙 *Xayrli oqshom!* 🌌\n"
        )


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
    f"🌤 *{name}* shahrining ayni vaqtdagi ob-havo ma'lumotlari ({sana} -yil , soat {soat})\n\n"
    f"🔸 Havo holati: *{weather}*\n"
    f"🌡 Harorat: *{temp}{degree_sign}* (Tuyulishi: {feels}{degree_sign})\n"
    f"💧 Namlik: {humidity}%\n"
    f"🌬 Shamol: {wind} m/s\n"
    f"🌅 Quyosh chiqishi: {sunrise}\n"
    f"🌇 Quyosh botishi: {sunset}\n\n"
    f"📍 *Tashkent vaqti bo‘yicha ma’lumot*"
)

    return msg

# === Xabar yuborish funksiyasi ===
async def send_weather():
    try:
        data = get_weather(CITY_NAME)
        text = format_weather_message(data)
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
        print(f"[{datetime.now()}] ✅ Xabar yuborildi")
    except Exception as e:
        print("❌ Xatolik:", e)

# === Rejalashtiruvchi (scheduler) ===
async def main():
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Har kuni 12:55 va 19:00 da yuborish
    times = [(23, 12), (23, 35)]
    for hour, minute in times:
        trigger = CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE)
        scheduler.add_job(send_weather, trigger=trigger)

    scheduler.start()

    print("✅ Scheduler ishga tushdi. Quyidagi vaqtlarda xabar yuboriladi:")
    for hour, minute in times:
        print(f" - {hour:02d}:{minute:02d}")

    # Botni fon rejimida ushlab turish
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
