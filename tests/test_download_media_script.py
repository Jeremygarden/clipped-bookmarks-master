# -*- coding: utf-8 -*-
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "download_media.sh"


def test_wechat_channels_message_says_not_downloaded(tmp_path):
    result = subprocess.run(
        ["bash", str(SCRIPT), "https://channels.weixin.qq.com/foo", "--dir", str(tmp_path)],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "未下载任何文件" in result.stdout
    assert "下载完成" not in result.stdout


def test_download_media_accepts_cookies_arg(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    yt_dlp = fake_bin / "yt-dlp"
    yt_dlp.write_text("#!/usr/bin/env bash\nprintf '%s\n' \"$@\" > \"$YT_DLP_ARGS_FILE\"\n", encoding="utf-8")
    yt_dlp.chmod(0o755)
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    args_file = tmp_path / "args.txt"

    import os
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}", "YT_DLP_ARGS_FILE": str(args_file)}
    result = subprocess.run(
        ["bash", str(SCRIPT), "https://example.com/video", "--dir", str(tmp_path / "out"), "--cookies", str(cookies)],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    assert "下载完成" in result.stdout
    args = args_file.read_text(encoding="utf-8")
    assert "--cookies" in args
    assert str(cookies) in args
