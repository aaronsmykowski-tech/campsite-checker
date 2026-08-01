import os
import json
import requests

CONFIG_FILE = 'config.json'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

def load_user_configs():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
    if isinstance(data, dict) and "users" in data:
        return data["users"]
    elif isinstance(data, dict) and "park_id" in data:
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        if chat_id: data["chat_id"] = chat_id
        return [data]
    elif isinstance(data, list):
        return data
    return []

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def send_telegram_alert(chat_id, park_name, park_id, start_date, end_date, site_number, site_id, loop_name="", electric=False):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    booking_url = f"https://www.reserveamerica.com/camping/detail?parkId={park_id}&siteId={site_id}"
    loop_str = f" ({loop_name})" if loop_name else ""
    
    msg = (
        f"🚨 <b>CAMPSITE AVAILABLE!</b>\n\n"
        f"📍 <b>Park:</b> {park_name}\n"
        f"📅 <b>Dates:</b> {start_date} to {end_date}\n"
        f"⛺ <b>Site:</b> #{site_number}{loop_str}\n"
        f"⚡ <b>Hookups:</b> {'Electric Required' if electric else 'Standard'}\n\n"
        f"👇 <i>Click below to book instantly on ReserveAmerica:</i>"
    )
    
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{"text": f"⛺ Book Site #{site_number} Now", "url": booking_url}]]
        }
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error posting alert to Telegram: {e}")

def check_user_availability(user):
    chat_id = user.get('chat_id')
    park_id = user.get('park_id', '70010')
    park_name = user.get('park_name', 'ReserveAmerica Park')
    start_date = user.get('start_date')
    end_date = user.get('end_date')
    target_sites = [str(s).strip() for s in user.get('target_sites', []) if str(s).strip()]
    electric_req = user.get('electric_required', False)

    if not chat_id or not start_date or not end_date:
        return

    grid_url = f"https://www.reserveamerica.com/api/availability/map?parkId={park_id}&startDate={start_date}&endDate={end_date}"
    
    try:
        res = requests.get(grid_url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return
        campsites = res.json().get('campsites', {})
        for site_id, site_info in campsites.items():
            site_num = str(site_info.get('siteNumber', '')).strip()
            is_available = site_info.get('available', False)
            
            if target_sites and site_num not in target_sites:
                continue
            if electric_req:
                has_electric = site_info.get('electricity', False) or 'electric' in str(site_info).lower()
                if not has_electric:
                    continue
                    
            if is_available:
                print(f"Match found for Chat ID {chat_id}! Site #{site_num} is AVAILABLE.")
                send_telegram_alert(chat_id, park_name, park_id, start_date, end_date, site_num, site_id, site_info.get('loop', ''), electric_req)
    except Exception as e:
        print(f"Error scanning {park_name} for user {chat_id}: {e}")

if __name__ == "__main__":
    users = load_user_configs()
    print(f"Loaded search profiles for {len(users)} user(s). Beginning scan...")
    for user in users:
        check_user_availability(user)
