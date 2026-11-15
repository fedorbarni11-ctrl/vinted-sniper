import os
import time
import json
import threading
import requests
from flask import Flask
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

KERESESEK = [
    {"kulcsszo": "Nike Air Max Plus TN", "max_ar": 22000, "min_profit": 8000},
    {"kulcsszo": "Jordan 4", "max_ar": 45000, "min_profit": 15000},
    {"kulcsszo": "Ralph Lauren polo", "max_ar": 12000, "min_profit": 6000},
]

VINTED_DOMAIN = "https://www.vinted.hu"
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

@app.route("/")
def home():
    return "Vinted Profit Sniper fut a háttérben! 🚀"

def telegram_uzenet_kuldes(szoveg: str, kep_url: str = None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if kep_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": kep_url, "caption": szoveg, "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": szoveg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Telegram hiba: {e}")

def hatter_sniper_futatas():
    latott_hirdetesek = set()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "hu-HU,hu;q=0.9",
    })
    
    while True:
        try:
            session.get(VINTED_DOMAIN, timeout=10)
            for elem in KERESESEK:
                kulcsszo = elem["kulcsszo"]
                max_ar = elem["max_ar"]
                min_profit = elem["min_profit"]

                api_url = f"{VINTED_DOMAIN}/api/v2/catalog/items"
                params = {"search_text": kulcsszo, "price_to": max_ar, "currency": "HUF", "order": "newest_first", "per_page": 5}
                response = session.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        item_id = item.get("id")
                        if item_id in latott_hirdetesek:
                            continue
                        latott_hirdetesek.add(item_id)

                        cim = item.get("title", "Nincs cím")
                        ar = float(item.get("price", {}).get("amount", 0))
                        marka = item.get("brand_title", "Ismeretlen")
                        meret = item.get("size_title", "Nincs megadva")
                        allapot = item.get("status", "Ismeretlen")
                        link = item.get("url", "")
                        kep = item.get("photo", {}).get("url", "")

                        prompt = f"""
                        Te egy profi magyar sneaker reseller vagy. Elemezd ezt a Vinted hirdetést:
                        - Cím: {cim}, Márka: {marka}, Méret: {meret}, Állapot: {allapot}
                        - Vételi ár: {ar} Ft (számolj rá 1500 Ft szállítás/védelem díjat).
                        Válaszolj KIZÁRÓLAG JSON formátumban:
                        {{"becsult_eladasi_ar_ft": int, "tiszta_profit_ft": int, "megeri": bool, "indoklas": "1 rövid mondat"}}
                        A "megeri" csak akkor true, ha a tiszta_profit_ft eléri a {min_profit} Ft-ot, és nem hamisítvány.
                        """
                        res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
                        elemzes = json.loads(res.text)

                        if elemzes and elemzes.get("megeri"):
                            uzenet = (
                                f"🔥 <b>PROFITOS DEAL!</b>\n\n"
                                f"👟 <b>{cim}</b>\n"
                                f"🏷️ {marka} | Méret: {meret}\n"
                                f"💵 Ár: <b>{int(ar):,} Ft</b>\n"
                                f"💰 Várható tiszta profit: <b>+{elemzes['tiszta_profit_ft']:,} Ft</b>\n\n"
                                f"🤖 <i>{elemzes['indoklas']}</i>\n\n"
                                f"🔗 <a href='{link}'>Megnyitás Vinteden</a>"
                            )
                            telegram_uzenet_kuldes(uzenet, kep)
                time.sleep(5)
        except Exception as e:
            print(f"Hiba: {e}")
        time.sleep(60)

t = threading.Thread(target=hatter_sniper_futatas)
t.daemon = True
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
