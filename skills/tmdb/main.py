"""TMDB (The Movie Database) integration skill — search movies/TV/people, get details,
discover titles, trending, watch providers, and recommendations via api.themoviedb.org v3.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (api_token, region).

Auth accepts EITHER a TMDB v3 API key (32-char hex) OR a v4 API Read Access Token (a JWT
starting with "eyJ"). The shape is detected automatically: a token containing "." is treated
as a JWT and sent as "Authorization: Bearer <token>"; anything else is sent as the
?api_key=<key> query parameter.

This product uses the TMDB API but is not endorsed or certified by TMDB.
Watch provider data is supplied by JustWatch and must be credited when displayed.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_token = (params.get("api_token") or "").strip()
default_region = ((params.get("region") or "").strip() or "US").upper()

API_BASE = "https://api.themoviedb.org/3"
JUSTWATCH_ATTRIBUTION = "Watch provider data provided by JustWatch."


def request(path, query=None):
    """GET a TMDB v3 API path. Returns parsed JSON (or None for 204/empty)."""
    clean = {k: v for k, v in (query or {}).items() if v not in (None, "")}
    headers = {
        "Accept": "application/json",
        "User-Agent": "sophon-tmdb-skill",
    }
    if "." in api_token:
        # v4 API Read Access Token (JWT) -> Bearer header
        headers["Authorization"] = f"Bearer {api_token}"
    else:
        # v3 API key -> query parameter
        clean["api_key"] = api_token
    url = f"{API_BASE}{path}"
    if clean:
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("status_message") or detail
        except (ValueError, TypeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After")
            hint = "rate limited, slow down"
            if retry_after:
                hint += f"; retry after {retry_after}s"
            raise RuntimeError(f"TMDB API error 429: {msg} ({hint})") from e
        raise RuntimeError(f"TMDB API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach TMDB: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def path_id(value, name):
    """Validate and URL-quote a params-derived path segment."""
    s = str(value if value is not None else "").strip()
    if not s:
        raise ValueError(f"{name} required")
    if s in (".", ".."):
        raise ValueError(f"Invalid {name}: {s!r}")
    return urllib.parse.quote(s, safe="")


def media_summary(item):
    return {
        "id": item.get("id"),
        "media_type": item.get("media_type"),
        "title": item.get("title") or item.get("name"),
        "release_date": item.get("release_date") or item.get("first_air_date"),
        "overview": (item.get("overview") or "")[:300],
        "vote_average": item.get("vote_average"),
    }


def title_summary(item):
    return {
        "id": item.get("id"),
        "title": item.get("title") or item.get("name"),
        "release_date": item.get("release_date") or item.get("first_air_date"),
        "overview": (item.get("overview") or "")[:300],
        "vote_average": item.get("vote_average"),
        "vote_count": item.get("vote_count"),
    }


def media_type_param(allowed, default):
    mt = (params.get("mediaType") or default).strip().lower()
    if mt not in allowed:
        raise ValueError(f"mediaType must be one of: {', '.join(sorted(allowed))}")
    return mt


# --- Tool handlers ---------------------------------------------------------

def search_media():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    page = clamp(params.get("page", 1), 1, 500)
    data = request("/search/multi", {
        "query": query,
        "page": page,
        "include_adult": "false",
    }) or {}
    results = [media_summary(r) for r in data.get("results", [])]
    print(json.dumps({
        "count": len(results),
        "page": data.get("page"),
        "total_results": data.get("total_results"),
        "results": results,
    }))


def get_movie_details():
    movie_id = path_id(params.get("movieId"), "movieId")
    data = request(f"/movie/{movie_id}", {
        "append_to_response": "credits,release_dates,keywords",
    }) or {}
    credits = data.get("credits") or {}
    cast = [{"name": c.get("name"), "character": c.get("character")}
            for c in (credits.get("cast") or [])[:10]]
    directors = [c.get("name") for c in (credits.get("crew") or [])
                 if c.get("job") == "Director"]
    keywords = [k.get("name")
                for k in ((data.get("keywords") or {}).get("keywords") or [])[:15]]
    certification = None
    for entry in ((data.get("release_dates") or {}).get("results") or []):
        if entry.get("iso_3166_1") == default_region:
            for rd in entry.get("release_dates") or []:
                if rd.get("certification"):
                    certification = rd["certification"]
                    break
            break
    print(json.dumps({
        "id": data.get("id"),
        "title": data.get("title"),
        "release_date": data.get("release_date"),
        "runtime": data.get("runtime"),
        "genres": [g.get("name") for g in data.get("genres") or []],
        "tagline": data.get("tagline"),
        "overview": data.get("overview"),
        "status": data.get("status"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "certification": certification,
        "directors": directors,
        "cast": cast,
        "keywords": keywords,
    }))


def get_tv_details():
    tv_id = path_id(params.get("tvId"), "tvId")
    season = params.get("season")
    if season is not None and str(season).strip() != "":
        season_seg = path_id(season, "season")
        data = request(f"/tv/{tv_id}/season/{season_seg}") or {}
        episodes = [{
            "episode_number": e.get("episode_number"),
            "name": e.get("name"),
            "air_date": e.get("air_date"),
            "vote_average": e.get("vote_average"),
            "overview": (e.get("overview") or "")[:200],
        } for e in data.get("episodes") or []]
        print(json.dumps({
            "id": data.get("id"),
            "name": data.get("name"),
            "season_number": data.get("season_number"),
            "air_date": data.get("air_date"),
            "overview": data.get("overview"),
            "episode_count": len(episodes),
            "episodes": episodes,
        }))
        return
    data = request(f"/tv/{tv_id}") or {}
    print(json.dumps({
        "id": data.get("id"),
        "name": data.get("name"),
        "first_air_date": data.get("first_air_date"),
        "last_air_date": data.get("last_air_date"),
        "number_of_seasons": data.get("number_of_seasons"),
        "number_of_episodes": data.get("number_of_episodes"),
        "genres": [g.get("name") for g in data.get("genres") or []],
        "overview": data.get("overview"),
        "status": data.get("status"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "networks": [n.get("name") for n in data.get("networks") or []],
        "created_by": [c.get("name") for c in data.get("created_by") or []],
    }))


def discover_titles():
    media_type = media_type_param({"movie", "tv"}, "movie")
    page = clamp(params.get("page", 1), 1, 500)
    query = {
        "with_genres": params.get("withGenres"),
        "vote_average.gte": params.get("minVoteAverage"),
        "sort_by": params.get("sortBy"),
        "page": page,
    }
    year = params.get("year")
    if year not in (None, ""):
        if media_type == "movie":
            query["primary_release_year"] = year
        else:
            query["first_air_date_year"] = year
    providers = params.get("withWatchProviders")
    if providers not in (None, ""):
        query["with_watch_providers"] = providers
        query["watch_region"] = ((params.get("watchRegion") or "").strip()
                                 or default_region).upper()
    data = request(f"/discover/{media_type}", query) or {}
    results = [title_summary(r) for r in data.get("results", [])]
    print(json.dumps({
        "count": len(results),
        "page": data.get("page"),
        "total_results": data.get("total_results"),
        "results": results,
    }))


def get_trending():
    media_type = media_type_param({"movie", "tv", "all"}, "all")
    window = (params.get("timeWindow") or "day").strip().lower()
    if window not in ("day", "week"):
        raise ValueError("timeWindow must be 'day' or 'week'")
    data = request(f"/trending/{media_type}/{window}") or {}
    results = [media_summary(r) for r in data.get("results", [])]
    print(json.dumps({
        "count": len(results),
        "time_window": window,
        "results": results,
    }))


def get_watch_providers():
    media_type = media_type_param({"movie", "tv"}, "movie")
    title_id = path_id(params.get("id"), "id")
    region = ((params.get("region") or "").strip() or default_region).upper()
    data = request(f"/{media_type}/{title_id}/watch/providers") or {}
    entry = (data.get("results") or {}).get(region) or {}

    def names(key):
        return [p.get("provider_name") for p in entry.get(key) or []]

    print(json.dumps({
        "id": data.get("id"),
        "region": region,
        "link": entry.get("link"),
        "flatrate": names("flatrate"),
        "rent": names("rent"),
        "buy": names("buy"),
        "attribution": JUSTWATCH_ATTRIBUTION,
    }))


def get_recommendations():
    media_type = media_type_param({"movie", "tv"}, "movie")
    title_id = path_id(params.get("id"), "id")
    page = clamp(params.get("page", 1), 1, 500)
    data = request(f"/{media_type}/{title_id}/recommendations", {"page": page}) or {}
    results = [media_summary(r) for r in data.get("results", [])]
    print(json.dumps({
        "count": len(results),
        "page": data.get("page"),
        "total_results": data.get("total_results"),
        "results": results,
    }))


HANDLERS = {
    "tmdb.search_media": search_media,
    "tmdb.get_movie_details": get_movie_details,
    "tmdb.get_tv_details": get_tv_details,
    "tmdb.discover_titles": discover_titles,
    "tmdb.get_trending": get_trending,
    "tmdb.get_watch_providers": get_watch_providers,
    "tmdb.get_recommendations": get_recommendations,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_token:
        print(json.dumps({"error": "Missing TMDB credentials: connect the TMDB integration first (api_token — a v3 API key or v4 Read Access Token)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
