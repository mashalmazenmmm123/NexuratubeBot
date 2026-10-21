import os


def _split_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_yt_dlp_options(extra=None):
    """Build yt-dlp options with YouTube anti-bot support.

    Supports the common anti-bot workarounds recommended by yt-dlp for YouTube:
    - PO Token and visitor data via extractor_args
    - browser cookie files from env vars
    - browser cookie import via cookiesfrombrowser
    - custom http headers used by browser clients
    """
    opts = {}
    extra = extra or {}

    yt_args = {}
    player_clients = _split_csv(os.environ.get("YOUTUBE_PLAYER_CLIENTS"))
    if player_clients:
        yt_args["player_client"] = player_clients
    else:
        yt_args["player_client"] = ["web", "android", "ios"]

    po_token = os.environ.get("YOUTUBE_PO_TOKEN")
    if po_token:
        yt_args["po_token"] = [po_token]

    visitor_data = os.environ.get("YOUTUBE_VISITOR_DATA")
    if visitor_data:
        yt_args["visitor_data"] = [visitor_data]

    if yt_args:
        opts["extractor_args"] = {"youtube": yt_args}

    cookie_file = os.environ.get("YOUTUBE_COOKIES_FILE") or os.environ.get("COOKIES_FILE")
    if cookie_file and os.path.exists(cookie_file):
        opts["cookies"] = cookie_file

    raw_cookies = os.environ.get("YOUTUBE_COOKIES")
    if raw_cookies and not opts.get("cookies"):
        opts["cookies"] = raw_cookies

    cookies_from_browser = os.environ.get("YOUTUBE_COOKIES_FROM_BROWSER")
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = _split_csv(cookies_from_browser)

    headers = {}
    user_agent = os.environ.get("YOUTUBE_USER_AGENT")
    if user_agent:
        headers["User-Agent"] = user_agent
    accept_language = os.environ.get("YOUTUBE_ACCEPT_LANGUAGE")
    if accept_language:
        headers["Accept-Language"] = accept_language

    client_name = os.environ.get("YOUTUBE_CLIENT_NAME")
    client_version = os.environ.get("YOUTUBE_CLIENT_VERSION")
    if client_name:
        headers["X-YouTube-Client-Name"] = client_name
    if client_version:
        headers["X-YouTube-Client-Version"] = client_version

    if headers:
        opts["http_headers"] = headers

    if extra:
        opts.update(extra)
    return opts
