from yt_dlp import YoutubeDL


def search_tracks(query, options=None, limit=10):
    query = str(query).strip()
    if not query:
        return None
    url = query if query.startswith(("http://", "https://")) else f"scsearch{limit}:{query}"
    with YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True, **(options or {})}) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries") or [info]
    results = []
    for item in entries:
        if not item:
            continue
        entry = dict(item)
        entry["url"] = entry.get("webpage_url") or entry.get("original_url") or entry.get("url")
        if not str(entry["url"]).startswith(("http://", "https://")) and entry.get("id"):
            entry["url"] = f"https://soundcloud.com/{entry['id']}"
        results.append(entry)
    return results


def search_track(query, options=None):
    return next(iter(search_tracks(query, options, limit=1)), None)
