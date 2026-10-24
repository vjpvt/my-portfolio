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
        return {"followers": "378", "viewers": 0}
    
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
                return {"followers": "378", "viewers": 0}
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
            "viewers": current_viewers
        }
    except Exception as e:
        print(f"Twitch API Error: {e}")
        return {"followers": "378", "viewers": 0}

def fetch_youtube_data():
    if not YOUTUBE_API_KEY:
        return {"subscribers": "---", "totalViews": "0", "featuredVideos": []}
    
    try:
        # 1. チャンネル基本統計（登録者・総再生数・アップロードプレイリストID）
        stats_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,contentDetails&id={YOUTUBE_CHANNEL_ID}&key={YOUTUBE_API_KEY}"
        req = urllib.request.Request(stats_url)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("items", [])
            if not items:
                return {"subscribers": "---", "totalViews": "0", "featuredVideos": []}
            
            stats = items[0]["statistics"]
            subs = stats.get("subscriberCount", "0")
            views = stats.get("viewCount", "0")
            
            uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. アップロード動画一覧を取得して再生数順にソートし、上位3つを抽出
        playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={uploads_playlist_id}&key={YOUTUBE_API_KEY}"
        req_pl = urllib.request.Request(playlist_url)
        featured_videos = []
        with urllib.request.urlopen(req_pl) as res_pl:
            pl_data = json.loads(res_pl.read().decode("utf-8"))
            videos = []
            for item in pl_data.get("items", []):
                snippet = item["snippet"]
                vid = snippet["resourceId"]["videoId"]
                title = snippet["title"]
                if title != "Private video" and title != "Deleted video":
                    videos.append({"videoId": vid, "title": title})

            # 各動画の詳細（再生数）を取得
            if videos:
                vids_str = ",".join([v["videoId"] for v in videos[:20]]) # 直近の20本を対象にチェック
                details_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={vids_str}&key={YOUTUBE_API_KEY}"
                req_det = urllib.request.Request(details_url)
                with urllib.request.urlopen(req_det) as res_det:
                    det_data = json.loads(res_det.read().decode("utf-8"))
                    vid_stats = []
                    for d in det_data.get("items", []):
                        v_id = d["id"]
                        v_views = int(d["statistics"].get("viewCount", 0))
                        # 対応するタイトルを探す
                        v_title = next((v["title"] for v in videos if v["videoId"] == v_id), "YouTube Video")
                        vid_stats.append({"title": v_title, "url": f"https://www.youtube.com/watch?v={v_id}", "views": f"{v_views:,}"})
                    
                    # 再生数が多い順にソートして上位3つを取得
                    vid_stats.sort(key=lambda x: int(x["views"].replace(",", "")), reverse=True)
                    featured_videos = vid_stats[:3]

        return {
            "subscribers": f"{int(subs):,}",
            "totalViews": f"{int(views):,}",
            "featuredVideos": featured_videos
        }
    except Exception as e:
        print(f"YouTube API Error: {e}")
    return {"subscribers": "---", "totalViews": "0", "featuredVideos": []}

def main():
    data_file = "data.json"
    old_data = {}
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

    history.append({
        "time": now_str,
        "viewers": int(current_viewers)
    })
    if len(history) > 100:
        history = history[-100:]

    valid_viewers = [h["viewers"] for h in history if h["viewers"] > 0]
    avg_viewers = int(sum(valid_viewers) / len(valid_viewers)) if valid_viewers else 4

    # 手動保持データの引き継ぎ
    max_viewers = old_data.get("maxViewers", "170")
    twitch_unique_avg = old_data.get("twitchUniqueAvg", "265")
    youtube_demographics = old_data.get("youtubeDemographics", {
        "gender": {"male": "93.6%", "female": "6.4%"},
        "age": {"core": "25–34歳 (45.5%)", "sub": "18–24歳 (32.8%)"}
    })
    
    # YouTube APIから自動取得できた場合はそれを優先、無ければ既存を維持
    featured_videos = youtube_info.get("featuredVideos", [])
    if not featured_videos:
        featured_videos = old_data.get("featuredVideos", [
            {"title": "YouTube Video #1", "url": "https://www.youtube.com/@Twitch_vjpvt", "views": "---"}
        ])

    new_data = {
        "twitchFollowers": twitch_info.get("followers", "378"),
        "xFollowers": old_data.get("xFollowers", "850"),
        "youtubeSubscribers": youtube_info.get("subscribers", "58"),
        "youtubeTotalViews": youtube_info.get("totalViews", "0"),
        "avgViewers": str(avg_viewers),
        "maxViewers": max_viewers,
        "twitchUniqueAvg": twitch_unique_avg,
        "youtubeDemographics": youtube_demographics,
        "featuredVideos": featured_videos,
        "lastUpdated": now_str,
        "history": history
    }

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print("data.json updated successfully with automatic top videos!")

if __name__ == "__main__":
    main()
