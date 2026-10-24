import os
import json
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.parse

# 1. ユーザー情報の設定
YOUTUBE_CHANNEL_ID = "UCFXQUC7qZprU9nYSV6fpeiA" 
TWITCH_USER_LOGIN = "vjpvt"

# 2. API認証情報の読み込み
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")

def get_twitch_token():
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        return None
    url = "https://id.twitch.tv/oauth2/token"
    data = urllib.parse.urlencode({
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data.get("access_token")
    except Exception as e:
        print(f"Twitch Token Error: {e}")
        return None

def fetch_twitch_data(token):
    if not token or not TWITCH_USER_LOGIN:
        return {"followers": "0", "viewers": 0}
    
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    
    user_url = f"https://api.twitch.tv/helix/users?login={TWITCH_USER_LOGIN}"
    req = urllib.request.Request(user_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            user_data = json.loads(res.read().decode("utf-8"))
            users = user_data.get("data", [])
            if not users:
                return {}
            user_id = users[0]["id"]
            
        # フォロワー数取得
        follow_url = f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={user_id}"
        req_f = urllib.request.Request(follow_url, headers=headers)
        with urllib.request.urlopen(req_f) as res:
            follow_data = json.loads(res.read().decode("utf-8"))
            total_followers = follow_data.get("total", 0)
            
        # ライブ配信中の視聴者数取得
        stream_url = f"https://api.twitch.tv/helix/streams?user_id={user_id}"
        req_s = urllib.request.Request(stream_url, headers=headers)
        current_viewers = 0
        with urllib.request.urlopen(req_s) as res:
            stream_data = json.loads(res.read().decode("utf-8"))
            streams = stream_data.get("data", [])
            if streams:
                current_viewers = streams[0].get("viewer_count", 0)
                
        return {
            "followers": f"{total_followers:,}",
            "viewers": current_viewer_int := current_viewers
        }
    except Exception as e:
        print(f"Twitch API Error: {e}")
        return {"followers": "378", "viewers": 0}

def fetch_youtube_data():
    if not YOUTUBE_API_KEY:
        return {"subscribers": "---"}
    
    try:
        stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={YOUTUBE_CHANNEL_ID}&key={YOUTUBE_API_KEY}"
        req = urllib.request.Request(stats_url)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("items", [])
            if items:
                subs = items[0]["statistics"].get("subscriberCount", "0")
                return {"subscribers": f"{int(subs):,}"}
    except Exception as e:
        print(f"YouTube API Error: {e}")
    return {"subscribers": "---"}

def main():
    data_file = "data.json"
    history = []
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                history = old_data.get("history", [])
        except Exception:
            pass

    token = get_twitch_token()
    twitch_info = fetch_twitch_data(token)
    youtube_info = fetch_youtube_data()

    jst = timezone(timedelta(hours=9))
    now_str = datetime.now(jst).strftime("%Y-%m-%d %H:%M")

    current_viewers = twitch_info.get("viewers", 0)

    # 履歴に今回の測定値を追加
    history.append({
        "time": now_str,
        "viewers": int(current_viewers)
    })
    if len(history) > 100:
        history = history[-100:]

    # 履歴データから平均視聴者数と最高同時視聴者数を自動計算
    valid_viewers = [h["viewers"] for h in history if h["viewers"] > 0]
    avg_viewers = int(sum(valid_viewers) / len(valid_viewers)) if valid_viewers else 0
    max_viewers = max([h["viewers"] for h in history]) if history else 0

    new_data = {
        "twitchFollowers": twitch_info.get("followers", "378"),
        "xFollowers": "850",
        "youtubeSubscribers": youtube_info.get("subscribers", "---"),
        "avgViewers": str(avg_viewers),
        "maxViewers": str(max_viewers),
        "airTime": "120h",
        "lastUpdated": now_str,
        "history": history
    }

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print("data.json updated successfully with automatic calculations!")

if __name__ == "__main__":
    main()
