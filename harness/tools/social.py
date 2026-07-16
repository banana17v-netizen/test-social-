import json, os, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from .base import tool_harness

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


# search.list costs 100 quota units/call regardless of maxResults (10k/day budget on a free
# Google Cloud project -> ~99 calls/day ceiling), so cache far longer than the other tools.
@tool_harness(cache_ttl=600)
def fetch_social_mentions(token: str, window_h: int = 72) -> dict:
    key = os.environ["YOUTUBE_API_KEY"]
    published_after = (datetime.now(timezone.utc) - timedelta(hours=window_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # YouTube has no ticker-aware search; appending "crypto" cuts down unrelated matches
    # (e.g. token "ETH" alone also matches unrelated non-crypto videos).
    search_params = {
        "part": "snippet", "q": f"{token} crypto", "type": "video", "order": "date",
        "publishedAfter": published_after, "maxResults": "50", "key": key,
    }
    req = urllib.request.Request(f"{SEARCH_URL}?{urllib.parse.urlencode(search_params)}")
    with urllib.request.urlopen(req, timeout=15) as response:
        search_raw = json.loads(response.read().decode())

    items = search_raw.get("items", [])
    if not items:
        raise ValueError(f"YouTube returned no videos mentioning {token}")
    video_ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]

    # videos.list is only 1 quota unit per call (batched, up to 50 ids) -- cheap enough to
    # always pull stats alongside the search instead of relying on search result count alone.
    stats_params = {"part": "statistics", "id": ",".join(video_ids), "key": key}
    req = urllib.request.Request(f"{VIDEOS_URL}?{urllib.parse.urlencode(stats_params)}")
    with urllib.request.urlopen(req, timeout=15) as response:
        stats_raw = json.loads(response.read().decode())

    views = [int(v["statistics"].get("viewCount", 0)) for v in stats_raw.get("items", [])]
    likes = [int(v["statistics"].get("likeCount", 0)) for v in stats_raw.get("items", [])]
    count = len(items)
    total_views, total_likes = sum(views), sum(likes)
    latest = max((it["snippet"]["publishedAt"] for it in items), default=None)
    latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00")) if latest else datetime.now(timezone.utc)

    return {
        "token": token.upper(),
        "summary": (f"{count} YouTube videos mentioning {token.upper()} in last {window_h}h, "
                    f"{total_views} total views, {total_likes} total likes"),
        "magnitude": max(0.0, min(1.0, count / 20)),
        "raw_numbers": [float(count), float(total_views), float(total_likes)],
        "timestamp": latest_dt.isoformat(),
    }
