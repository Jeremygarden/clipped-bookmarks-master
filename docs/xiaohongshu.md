# Xiaohongshu / 小红书 support

Supports single image-text/video notes, `xhslink.cn` short-link expansion, collection link expansion to note URLs, Playwright logged-in-session first fetch, requests fallback, media downloads, a pluggable OCR hook with safe stub fallback, login/anti-bot/rate-limit detection, and error status reporting.

CLI helpers:

```bash
python3 scripts/xhs_expand.py 'https://xhslink.cn/o/2HSnq3KBHMZ' --json
python3 scripts/xhs_download_media.py 'https://www.xiaohongshu.com/explore/<note_id>' --out xhs_media
```

Login-state notes: full note content, private/deep collections, high-resolution images, and short-video URLs often need an authenticated Playwright browser profile. Requests fallback is best-effort for public HTML only. Bilibili is intentionally not supported.
