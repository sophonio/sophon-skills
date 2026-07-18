"""Offline mock-HTTP integration tests for the tmdb skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://api.themoviedb.org/3"
V3_KEY = "5ecfe70ba1c8f9a3d47b2260e91c8d4f"  # 32-hex-style v3 key (no dots)
V4_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJ0bWRiLVNFQ1JFVCJ9.sig-SECRET-v4"  # JWT-shaped


def creds_v3(**extra):
    p = {"api_token": V3_KEY, "region": "US"}
    p.update(extra)
    return p


def creds_v4(**extra):
    p = {"api_token": V4_TOKEN, "region": "US"}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. AUTH EXACTNESS — v3 key goes in ?api_key=, v4 JWT goes in Bearer header
# ---------------------------------------------------------------------------
print("scenario: v3 key sent as api_key query param, never as a header")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.search_media", query="dune"), [
    resp(200, body={"page": 1, "total_results": 1, "results": [
        {"id": 693134, "media_type": "movie", "title": "Dune: Part Two",
         "release_date": "2024-02-27", "overview": "Follow the mythic journey...",
         "vote_average": 8.2, "popularity": 999.9, "backdrop_path": "/x.jpg",
         "genre_ids": [878, 12]},
    ]}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (api_key last)",
            ex[0].url == f"{BASE}/search/multi?query=dune&page=1&include_adult=false&api_key={V3_KEY}",
            ex[0].url)
ok &= check("no Authorization header with v3 key",
            "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("User-Agent is sophon-tmdb-skill",
            ex[0].headers.get("user-agent") == "sophon-tmdb-skill", str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
r0 = out["results"][0]
ok &= check("trimmed fields present",
            r0["id"] == 693134 and r0["media_type"] == "movie"
            and r0["title"] == "Dune: Part Two" and r0["release_date"] == "2024-02-27",
            str(r0))
ok &= check("raw fields absent (backdrop_path/genre_ids/popularity)",
            "backdrop_path" not in r0 and "genre_ids" not in r0 and "popularity" not in r0,
            str(r0))
ok &= check("v3 key not echoed in output", V3_KEY not in json.dumps(out))

print("scenario: v4 JWT sent as 'Bearer <token>' header, never as api_key")
out, ex = run_tool("tmdb", creds_v4(tool="tmdb.get_trending",
                                    mediaType="all", timeWindow="week"), [
    resp(200, body={"page": 1, "results": [
        {"id": 1, "media_type": "tv", "name": "Severance",
         "first_air_date": "2022-02-17", "overview": "Mark leads a team...",
         "vote_average": 8.4},
    ]}),
])
ok &= check("trending URL byte-exact (no query string with v4)",
            ex[0].url == f"{BASE}/trending/all/week", ex[0].url)
ok &= check("Authorization is exactly 'Bearer <token>'",
            ex[0].headers.get("authorization") == f"Bearer {V4_TOKEN}", str(ex[0].headers))
ok &= check("api_key absent from URL with v4 token", "api_key" not in ex[0].url, ex[0].url)
ok &= check("trending shaped: name mapped to title",
            out == {"count": 1, "time_window": "week", "results": [
                {"id": 1, "media_type": "tv", "title": "Severance",
                 "release_date": "2022-02-17", "overview": "Mark leads a team...",
                 "vote_average": 8.4}]},
            str(out))
ok &= check("v4 token not echoed in output", V4_TOKEN not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. tmdb.get_movie_details — happy path with append_to_response shaping
# ---------------------------------------------------------------------------
print("scenario: get_movie_details happy path")
out, ex = run_tool("tmdb", creds_v4(tool="tmdb.get_movie_details", movieId="550"), [
    resp(200, body={
        "id": 550, "title": "Fight Club", "release_date": "1999-10-15",
        "runtime": 139, "tagline": "Mischief. Mayhem. Soap.",
        "overview": "A ticking-time-bomb insomniac...", "status": "Released",
        "vote_average": 8.4, "vote_count": 27000,
        "genres": [{"id": 18, "name": "Drama"}],
        "budget": 63000000, "revenue": 100853753, "backdrop_path": "/z.jpg",
        "production_companies": [{"id": 1, "name": "Fox"}],
        "credits": {
            "cast": [{"name": "Edward Norton", "character": "The Narrator",
                      "profile_path": "/a.jpg", "order": 0},
                     {"name": "Brad Pitt", "character": "Tyler Durden", "order": 1}],
            "crew": [{"name": "David Fincher", "job": "Director"},
                     {"name": "Jim Uhls", "job": "Screenplay"}],
        },
        "release_dates": {"results": [
            {"iso_3166_1": "DE", "release_dates": [{"certification": "18"}]},
            {"iso_3166_1": "US", "release_dates": [{"certification": ""},
                                                   {"certification": "R"}]},
        ]},
        "keywords": {"keywords": [{"id": 1, "name": "dual identity"},
                                  {"id": 2, "name": "support group"}]},
    }),
])
ok &= check("URL byte-exact (append_to_response encoded)",
            ex[0].url == f"{BASE}/movie/550?append_to_response=credits%2Crelease_dates%2Ckeywords",
            ex[0].url)
ok &= check("Bearer auth", ex[0].headers.get("authorization") == f"Bearer {V4_TOKEN}")
ok &= check("core fields shaped",
            out["title"] == "Fight Club" and out["runtime"] == 139
            and out["genres"] == ["Drama"], str(out)[:300])
ok &= check("directors extracted from crew", out["directors"] == ["David Fincher"],
            str(out.get("directors")))
ok &= check("cast trimmed to name/character",
            out["cast"][0] == {"name": "Edward Norton", "character": "The Narrator"},
            str(out.get("cast")))
ok &= check("US certification picked (region field)", out["certification"] == "R",
            str(out.get("certification")))
ok &= check("keywords flattened", out["keywords"] == ["dual identity", "support group"],
            str(out.get("keywords")))
ok &= check("raw fields absent (budget/credits/release_dates)",
            "budget" not in out and "credits" not in out and "release_dates" not in out
            and "production_companies" not in out, str(out)[:400])

# ---------------------------------------------------------------------------
# 3. tmdb.get_tv_details — show and season variants
# ---------------------------------------------------------------------------
print("scenario: get_tv_details show happy path")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_tv_details", tvId="1399"), [
    resp(200, body={"id": 1399, "name": "Game of Thrones",
                    "first_air_date": "2011-04-17", "last_air_date": "2019-05-19",
                    "number_of_seasons": 8, "number_of_episodes": 73,
                    "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}],
                    "overview": "Seven noble families...", "status": "Ended",
                    "vote_average": 8.5, "vote_count": 24000,
                    "networks": [{"id": 49, "name": "HBO"}],
                    "created_by": [{"id": 9813, "name": "David Benioff"}],
                    "seasons": [{"raw": "list"}], "production_companies": []}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/tv/1399?api_key={V3_KEY}", ex[0].url)
ok &= check("show shaped (networks/creators flattened)",
            out["name"] == "Game of Thrones" and out["networks"] == ["HBO"]
            and out["created_by"] == ["David Benioff"]
            and out["number_of_seasons"] == 8, str(out)[:300])
ok &= check("raw seasons list absent", "seasons" not in out, str(out)[:300])

print("scenario: get_tv_details with season -> /tv/{id}/season/{n}")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_tv_details", tvId="1399", season=2), [
    resp(200, body={"id": 3625, "name": "Season 2", "season_number": 2,
                    "air_date": "2012-04-01", "overview": "The cold winds...",
                    "episodes": [{"episode_number": 1, "name": "The North Remembers",
                                  "air_date": "2012-04-01", "vote_average": 8.0,
                                  "overview": "As Robb Stark...", "crew": [{"x": 1}],
                                  "still_path": "/s.jpg"}]}),
])
ok &= check("season URL byte-exact",
            ex[0].url == f"{BASE}/tv/1399/season/2?api_key={V3_KEY}", ex[0].url)
ok &= check("episode_count and shaped episodes",
            out["episode_count"] == 1
            and out["episodes"][0]["name"] == "The North Remembers"
            and "crew" not in out["episodes"][0]
            and "still_path" not in out["episodes"][0], str(out)[:400])

# ---------------------------------------------------------------------------
# 4. tmdb.discover_titles — filter mapping incl. year key per media type
# ---------------------------------------------------------------------------
print("scenario: discover_titles tv maps filters and defaults watch_region")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.discover_titles", mediaType="tv",
                                    withGenres="18", year=2024, minVoteAverage=8,
                                    withWatchProviders="8",
                                    sortBy="vote_average.desc"), [
    resp(200, body={"page": 1, "total_results": 1, "results": [
        {"id": 42, "name": "Shogun", "first_air_date": "2024-02-27",
         "overview": "In Japan in 1600...", "vote_average": 8.6, "vote_count": 1500,
         "genre_ids": [18], "origin_country": ["US"]},
    ]}),
])
ok &= check("discover URL byte-exact (first_air_date_year, watch_region from field)",
            ex[0].url == f"{BASE}/discover/tv?with_genres=18&vote_average.gte=8"
                         f"&sort_by=vote_average.desc&page=1&first_air_date_year=2024"
                         f"&with_watch_providers=8&watch_region=US&api_key={V3_KEY}",
            ex[0].url)
ok &= check("discover results shaped",
            out["count"] == 1 and out["results"][0]["title"] == "Shogun"
            and "genre_ids" not in out["results"][0], str(out)[:300])

print("scenario: discover_titles rejects bad mediaType, no HTTP call")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.discover_titles", mediaType="person"), [])
ok &= check("mediaType validation error",
            "mediaType" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 5. tmdb.get_watch_providers — region filtering + JustWatch attribution
# ---------------------------------------------------------------------------
print("scenario: get_watch_providers filters to region and credits JustWatch")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_watch_providers", id="136315",
                                    mediaType="tv", region="de"), [
    resp(200, body={"id": 136315, "results": {
        "US": {"link": "https://www.themoviedb.org/tv/136315/watch?locale=US",
               "flatrate": [{"provider_name": "Hulu", "provider_id": 15}]},
        "DE": {"link": "https://www.themoviedb.org/tv/136315/watch?locale=DE",
               "flatrate": [{"provider_name": "Disney Plus", "provider_id": 337}],
               "buy": [{"provider_name": "Apple TV", "provider_id": 2}]},
    }}),
])
ok &= check("providers URL byte-exact",
            ex[0].url == f"{BASE}/tv/136315/watch/providers?api_key={V3_KEY}", ex[0].url)
ok &= check("region param uppercased and filtered to DE",
            out["region"] == "DE" and out["flatrate"] == ["Disney Plus"]
            and out["buy"] == ["Apple TV"] and "Hulu" not in json.dumps(out),
            str(out))
ok &= check("empty rent list present", out["rent"] == [], str(out))
ok &= check("JustWatch attribution in output",
            out.get("attribution") == "Watch provider data provided by JustWatch.",
            str(out))

# ---------------------------------------------------------------------------
# 6. tmdb.get_recommendations — happy path
# ---------------------------------------------------------------------------
print("scenario: get_recommendations happy path")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_recommendations", id="550",
                                    mediaType="movie"), [
    resp(200, body={"page": 1, "total_results": 1, "results": [
        {"id": 807, "media_type": "movie", "title": "Se7en",
         "release_date": "1995-09-22", "overview": "Two homicide detectives...",
         "vote_average": 8.4, "poster_path": "/p.jpg"},
    ]}),
])
ok &= check("recommendations URL byte-exact",
            ex[0].url == f"{BASE}/movie/550/recommendations?page=1&api_key={V3_KEY}",
            ex[0].url)
ok &= check("shaped with count", out["count"] == 1 and out["results"][0]["title"] == "Se7en"
            and "poster_path" not in out["results"][0], str(out)[:300])

# ---------------------------------------------------------------------------
# 7. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error, no traceback, no secret")
out, ex = run_tool("tmdb", creds_v4(tool="tmdb.get_movie_details", movieId="550"), [
    err(401, body={"status_code": 7,
                   "status_message": "Invalid API key: You must be granted a valid key.",
                   "success": False}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes TMDB status_message",
            "Invalid API key" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("v4 token not leaked in error", V4_TOKEN not in raw, raw[:300])

print("scenario: 429 includes rate-limit hint and Retry-After")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.search_media", query="x"), [
    err(429, body={"status_code": 25,
                   "status_message": "Your request count is over the allowed limit."},
        headers={"Retry-After": "7"}),
])
ok &= check("429 surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("slow-down hint present", "rate limited, slow down" in out["error"],
            out.get("error", ""))
ok &= check("Retry-After seconds included", "7" in out["error"], out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.search_media", query="x"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"]
            and "Traceback" not in json.dumps(out), str(out)[:300])

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.search_media"), [])
ok &= check("query required error", out.get("error") == "query required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> connect-first error, no HTTP call")
out, ex = run_tool("tmdb", {"tool": "tmdb.search_media", "query": "dune"}, [])
ok &= check("connect-first message names api_token",
            "connect the TMDB integration" in out.get("error", "")
            and "api_token" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: tmdb.nope", str(out))

# ---------------------------------------------------------------------------
# 8. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal movieId is percent-encoded")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_movie_details",
                                    movieId="550/../../account?x=1"), [
    resp(200, body={"id": 550, "title": "x"}),
])
path_part = ex[0].url.split("?", 1)[0]
ok &= check("id fully quoted in URL (no path escape)",
            path_part == f"{BASE}/movie/550%2F..%2F..%2Faccount%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' in URL", "../" not in ex[0].url, ex[0].url)

print("scenario: bare '..' id rejected outright, no HTTP call")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_recommendations", id=".."), [])
ok &= check("dot-dot id rejected", "Invalid id" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: traversal tvId/season quoted on season endpoint")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_tv_details", tvId="1399",
                                    season="2/../../configuration"), [
    resp(200, body={"id": 1, "episodes": []}),
])
ok &= check("season segment quoted",
            ex[0].url.split("?", 1)[0]
            == f"{BASE}/tv/1399/season/2%2F..%2F..%2Fconfiguration", ex[0].url)

print("scenario: secrets never appear in any output (error path)")
out, ex = run_tool("tmdb", creds_v3(tool="tmdb.get_trending"), [
    err(403, body={"status_message": "forbidden"}),
])
ok &= check("v3 key absent from error output", V3_KEY not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
