"""Xiaohongshu extraction helpers with Playwright-first fetching and requests fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
import json, re, time
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol
from urllib.parse import unquote, urljoin, urlparse, urlunparse

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

from clipped_bookmarks.schema import BookmarkAsset, BookmarkItem, Platform, SourceType

NOTE_PATH_RE = re.compile(r"/(?:explore|discovery/item)/([A-Za-z0-9_-]{8,64})")
COLLECTION_PATH_RE = re.compile(r"/collection/item/([A-Za-z0-9_-]{8,64})")
NOTE_URL_RE = re.compile(r'https?://(?:www\.)?xiaohongshu\.com/(?:explore|discovery/item)/[A-Za-z0-9_-]+(?:\?[^"\'<>\s]*)?', re.I)
IMAGE_RE = re.compile(r'https?://[^"\'<>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\'<>\s]*)?', re.I)
VIDEO_RE = re.compile(r'https?://[^"\'<>\s]+?\.(?:mp4|m3u8)(?:\?[^"\'<>\s]*)?', re.I)
SCRIPT_RE = re.compile(r'<script[^>]+id=["\'](__INITIAL_STATE__|initial-state|__NEXT_DATA__)["\'][^>]*>(.*?)</script>', re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
LOGIN_WALL_MARKERS = ("登录后查看", "登录以查看更多", "请登录", "验证码", "captcha", "滑块", "安全验证", "访问频繁", "risk")
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/124 Safari/537.36", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
OCRHook = Callable[[bytes, str | None], str | None]

class PlaywrightSession(Protocol):
    def fetch_html(self, url: str) -> str: ...

@dataclass(slots=True)
class XHSResult:
    ok: bool
    status: str
    url: str
    final_url: str | None = None
    item: BookmarkItem | None = None
    note_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    requires_login: bool = False
    retry_after: float | None = None

@dataclass(slots=True)
class XiaohongshuExtractor:
    session: Any = None
    playwright: PlaywrightSession | None = None
    ocr_hook: OCRHook | None = None
    rate_limit_seconds: float = 1.0
    timeout: float = 15.0
    download_dir: str | Path | None = None
    max_redirects: int = 5
    _last_request_at: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.session is None and requests is not None:
            self.session = requests.Session()
        if self.download_dir is not None:
            Path(self.download_dir).mkdir(parents=True, exist_ok=True)

    def extract(self, url: str) -> BookmarkItem:
        result = self.extract_result(url)
        if result.item:
            return result.item
        return BookmarkItem(url=url, platform=Platform.XIAOHONGSHU, source_type=SourceType.XIAOHONGSHU_COLLECTION if is_collection_url(url) else SourceType.XIAOHONGSHU_NOTE, title="Xiaohongshu extraction failed", status="error", errors=result.errors or [result.status], metadata={"xhs_status": result.status, "requires_login": result.requires_login, "final_url": result.final_url, "retry_after": result.retry_after})

    def extract_result(self, url: str) -> XHSResult:
        final_url = self.expand_short_link(url)
        html = self._fetch_html_logged_in_first(final_url)
        if html is None:
            return XHSResult(False, "fetch_failed", url, final_url, errors=["Unable to fetch page"])
        wall = detect_access_wall(html)
        if wall:
            return self._wall_item(url, final_url, wall)
        return self._extract_collection(url, final_url, html) if is_collection_url(final_url) else self._extract_note(url, final_url, html)

    def expand_short_link(self, url: str) -> str:
        current = normalize_xhs_url(url)
        if not urlparse(current).netloc.lower().endswith("xhslink.cn") or self.session is None:
            return current
        for _ in range(self.max_redirects):
            self._rate_limit()
            response = self.session.get(current, headers=DEFAULT_HEADERS, timeout=self.timeout, allow_redirects=False)
            location = response.headers.get("Location") or response.headers.get("location")
            if location and 300 <= getattr(response, "status_code", 0) < 400:
                current = urljoin(current, location)
                if not urlparse(current).netloc.lower().endswith("xhslink.cn"):
                    return normalize_xhs_url(current)
            elif getattr(response, "url", None) and response.url != current:
                return normalize_xhs_url(response.url)
            else:
                return normalize_xhs_url(current)
        return normalize_xhs_url(current)

    def expand_collection(self, url: str) -> list[str]:
        html = self._fetch_html_logged_in_first(self.expand_short_link(url)) or ""
        return extract_note_urls_from_html(html)

    def download_media(self, assets: Iterable[BookmarkAsset], download_dir: str | Path | None = None) -> list[BookmarkAsset]:
        if self.session is None:
            raise RuntimeError("requests is required to download Xiaohongshu media")
        target = Path(download_dir or self.download_dir or "xhs_media"); target.mkdir(parents=True, exist_ok=True)
        out: list[BookmarkAsset] = []
        for i, asset in enumerate(assets, 1):
            self._rate_limit(); response = self.session.get(asset.url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            copied = BookmarkAsset(**asset.to_dict())
            if getattr(response, "status_code", 200) >= 400:
                copied.metadata["download_status"] = f"http_{response.status_code}"; out.append(copied); continue
            path = target / f"xhs_{i:03d}{_suffix_from_url(asset.url, '.jpg' if asset.kind == 'image' else '.mp4')}"
            path.write_bytes(response.content); copied.local_path = str(path); copied.metadata["download_status"] = "ok"; out.append(copied)
        return out

    def ocr_image(self, image_bytes: bytes, mime_type: str | None = None) -> str | None:
        if self.ocr_hook is None: return None
        try: return self.ocr_hook(image_bytes, mime_type)
        except Exception as exc: return f"[ocr_error: {exc}]"

    def _fetch_html_logged_in_first(self, url: str) -> str | None:
        if self.playwright is not None:
            try:
                html = self.playwright.fetch_html(url)
                if html: return html
            except Exception: pass
        if self.session is None: return None
        try:
            self._rate_limit(); response = self.session.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
            if getattr(response, "status_code", 0) == 429: return "<html><body>访问频繁</body></html>"
            if getattr(response, "status_code", 0) >= 400: return None
            return response.text
        except Exception: return None

    def _extract_note(self, original: str, final: str, html: str) -> XHSResult:
        data = parse_xhs_html(html); assets = [BookmarkAsset(u, "image") for u in data["images"]] + [BookmarkAsset(u, "video") for u in data["videos"]]
        item = BookmarkItem(url=final, platform=Platform.XIAOHONGSHU, source_type=SourceType.XIAOHONGSHU_NOTE, title=data["title"] or "Xiaohongshu note", author=data["author"], content=data["description"] or data["title"] or "", tags=data["tags"], assets=assets, status="fetched", metadata={"original_url": original, "note_id": extract_note_id(final), "note_type": "video" if data["videos"] else "image_text", "xhs_status": "ok", "requires_login": False, "ocr_available": self.ocr_hook is not None, "playwright_used": self.playwright is not None})
        return XHSResult(True, "ok", original, final, item=item)

    def _extract_collection(self, original: str, final: str, html: str) -> XHSResult:
        note_urls = extract_note_urls_from_html(html); ok = bool(note_urls)
        item = BookmarkItem(url=final, platform=Platform.XIAOHONGSHU, source_type=SourceType.XIAOHONGSHU_COLLECTION, title=parse_xhs_html(html)["title"] or "Xiaohongshu collection", content="\n".join(note_urls), status="fetched" if ok else "error", errors=[] if ok else ["No note URLs found; collection may require login"], metadata={"original_url": original, "collection_id": extract_collection_id(final), "note_urls": note_urls, "xhs_status": "ok" if ok else "empty_collection_or_login_required", "requires_login": not ok})
        return XHSResult(ok, item.metadata["xhs_status"], original, final, item=item, note_urls=note_urls, errors=item.errors)

    def _wall_item(self, original: str, final: str, reason: str) -> XHSResult:
        retry = self.rate_limit_seconds if "频繁" in reason or "rate" in reason.lower() else None
        item = BookmarkItem(url=final, platform=Platform.XIAOHONGSHU, source_type=SourceType.XIAOHONGSHU_COLLECTION if is_collection_url(final) else SourceType.XIAOHONGSHU_NOTE, title="Xiaohongshu login or anti-bot wall", status="error", errors=[reason], metadata={"original_url": original, "xhs_status": "login_or_antibot_wall", "requires_login": True, "retry_after": retry})
        return XHSResult(False, "login_or_antibot_wall", original, final, item=item, errors=[reason], requires_login=True, retry_after=retry)

    def _rate_limit(self) -> None:
        if self.rate_limit_seconds <= 0: return
        elapsed = time.monotonic() - self._last_request_at
        if self._last_request_at and elapsed < self.rate_limit_seconds: time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_at = time.monotonic()

def normalize_xhs_url(url: str) -> str:
    p = urlparse(url.strip()); scheme = p.scheme or "https"; netloc = p.netloc or p.path.split("/")[0]; path = p.path if p.netloc else "/" + "/".join(p.path.split("/")[1:])
    return urlunparse((scheme, netloc.lower(), path.rstrip("/"), "", "", ""))
def is_collection_url(url: str) -> bool: return COLLECTION_PATH_RE.search(urlparse(url).path) is not None
def extract_note_id(url: str) -> str | None: return (m.group(1) if (m := NOTE_PATH_RE.search(urlparse(url).path)) else None)
def extract_collection_id(url: str) -> str | None: return (m.group(1) if (m := COLLECTION_PATH_RE.search(urlparse(url).path)) else None)
def detect_access_wall(html: str) -> str | None:
    low = html.lower()
    for marker in LOGIN_WALL_MARKERS:
        if marker.lower() in low: return f"Xiaohongshu login/anti-bot marker detected: {marker}"
    return None

def parse_xhs_html(html: str) -> dict[str, Any]:
    title = _unescape(_meta(html, "og:title") or _meta(html, "twitter:title") or _title(html)); desc = _unescape(_meta(html, "description") or _meta(html, "og:description") or ""); author = _unescape(_meta(html, "author") or "") or None
    images, videos = _dedupe(IMAGE_RE.findall(html)), _dedupe(VIDEO_RE.findall(html)); state = _json_state(html)
    if state:
        title = title or _deep_first(state, ("title", "displayTitle")) or ""; desc = desc or _deep_first(state, ("desc", "description", "content")) or ""; author = author or _deep_first(state, ("nickname", "nickName", "userName")); images = _dedupe([*images, *_deep_urls(state, image=True)]); videos = _dedupe([*videos, *_deep_urls(state, video=True)])
    return {"title": title.strip(), "description": desc.strip(), "author": author, "tags": sorted({t for t in re.findall(r"#([\w\u4e00-\u9fff-]+)", desc)}), "images": images, "videos": videos}

def extract_note_urls_from_html(html: str) -> list[str]:
    urls = {normalize_xhs_url(unquote(u)) for u in NOTE_URL_RE.findall(html)}
    text = html.replace("\\/", "/").replace("\\u002F", "/")
    urls |= {normalize_xhs_url(unquote(u)) for u in NOTE_URL_RE.findall(text)}
    return sorted(urls)
def _meta(html: str, name: str) -> str:
    m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(name) + r'["\'][^>]+content=["\'](.*?)["\']', html, re.I | re.S); return m.group(1) if m else ""
def _title(html: str) -> str: return (m.group(1) if (m := TITLE_RE.search(html)) else "")
def _json_state(html: str) -> Any:
    for _, payload in SCRIPT_RE.findall(html):
        try: return json.loads(_unescape(payload.strip()))
        except Exception: pass
    return None
def _deep_first(obj: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str) and v.strip(): return v
            if (r := _deep_first(v, keys)): return r
    if isinstance(obj, list):
        for v in obj:
            if (r := _deep_first(v, keys)): return r
    return None
def _deep_urls(obj: Any, image=False, video=False) -> list[str]:
    out=[]
    if isinstance(obj, dict):
        for v in obj.values(): out += _deep_urls(v, image, video)
    elif isinstance(obj, list):
        for v in obj: out += _deep_urls(v, image, video)
    elif isinstance(obj, str) and obj.startswith("http"):
        low=obj.lower()
        if image and re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", low): out.append(obj)
        if video and re.search(r"\.(mp4|m3u8)(\?|$)", low): out.append(obj)
    return out
def _dedupe(vals: Iterable[str]) -> list[str]:
    seen=set(); out=[]
    for v in vals:
        c=_unescape(v).replace("\\/", "/")
        if c not in seen: seen.add(c); out.append(c)
    return out
def _unescape(v: str) -> str: return v.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
def _suffix_from_url(url: str, default: str) -> str:
    s = Path(urlparse(url).path).suffix.lower(); return s if s in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".m3u8"} else default
