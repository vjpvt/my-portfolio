import os
import json
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.parse

# 1. ユーザー情報の設定
YOUTUBE_HANDLE = "@VJPVTch" # 検索用のハンドル名
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
        return {"followers": "---", "viewers": "0", "maxViewers": "120", "airTime": "120h"}
    
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
            
        follow_url = f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={user_id}"
        req_f = urllib.request.Request(follow_url, headers=headers)
        with urllib.request.urlopen(req_f) as res:
            follow_data = json.loads(res.read().decode("utf-8"))
            total_followers = follow_data.get("total", 0)
            
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
            "viewers": str(current_viewers),
            "maxViewers": "120",
            "airTime": "120h"
        }
    except Exception as e:
        print(f"Twitch API Error: {e}")
        return {}

def fetch_youtube_data():
    if not YOUTUBE_API_KEY:
        return {"subscribers": "---"}
    
    try:
        # 1. ハンドル名からチャンネルIDを検索
        encoded_handle = urllib.parse.quote(YOUTUBE_HANDLE)
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={encoded_handle}&key={YOUTUBE_API_KEY}"
        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("items", [])
            if not items:
                return {"subscribers": "---"}
            channel_id = items[0]["snippet"]["channelId"]
            
        # 2. チャンネルIDを使って統計情報を取得
        stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={YOUTUBE_API_KEY}"
        req_s = urllib.request.Request(stats_url)
        with urllib.request.urlopen(req_s) as res:
            stats_data = json.loads(res.read().decode("utf-8"))
            stats_items = stats_data.get("items", [])
            if stats_items:
                subs = stats_items[0]["statistics"].get("subscriberCount", "0")
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

    new_data = {
        "twitchFollowers": twitch_info.get("followers", "378"),
        "xFollowers": "850",
        "youtubeSubscribers": youtube_info.get("subscribers", "---"),
        "avgViewers": twitch_info.get("viewers", "0"),
        "maxViewers": twitch_info.get("maxViewers", "120"),
        "airTime": twitch_info.get("airTime", "120h"),
        "lastUpdated": now_str
    }

    history.append({
        "time": now_str,
        "viewers": int(twitch_info.get("viewers", "0") if str(twitch_info.get("viewers", "0")).isdigit() else 0)
    })
    if len(history) > 100:
        history = history[-100:]
    
    new_data["history"] = history

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print("data.json updated successfully!")

if __name__ == "__main__":
    main()
