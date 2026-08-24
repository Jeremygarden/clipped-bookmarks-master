from pathlib import Path

from clipped_bookmarks.cli import main


def test_process_url_wechat_html_fixture_writes_markdown(tmp_path: Path):
    html = tmp_path / "wechat.html"
    html.write_text(
        '''<html><head><meta property="og:url" content="https://mp.weixin.qq.com/s/abc123" /></head><body><h1 id="activity-name">微信标题</h1><span id="js_name">公众号</span><div id="js_content"><p>微信正文第一段。</p><p>微信正文第二段。</p></div></body></html>''',
        encoding="utf-8",
    )
    out = tmp_path / "notes"

    assert main(["process-url", str(html), "--out", str(out)]) == 0
    [note] = list(out.glob("*.md"))
    text = note.read_text(encoding="utf-8")
    assert "# 微信标题" in text
    assert "微信正文第一段" in text
    assert "wechat_official_account" in text


def test_process_url_zhihu_html_fixture_writes_markdown(tmp_path: Path):
    html = tmp_path / "zhihu.html"
    html.write_text(
        '''<html><head><meta property="og:url" content="https://www.zhihu.com/question/1/answer/2" /></head><body><h1>知乎标题</h1><div class="AnswerCard"><a class="AuthorInfo-name">作者甲</a><div class="RichText"><p>知乎回答正文。</p></div></div></body></html>''',
        encoding="utf-8",
    )
    out = tmp_path / "notes"

    assert main(["process-url", str(html), "--out", str(out)]) == 0
    [note] = list(out.glob("*.md"))
    text = note.read_text(encoding="utf-8")
    assert "# 知乎标题" in text
    assert "知乎回答正文" in text
    assert "zhihu" in text


def test_process_url_transcript_local_file_writes_markdown(tmp_path: Path):
    transcript = tmp_path / "clip.srt"
    transcript.write_text("1\n00:00:00,000 --> 00:00:02,000\nhello transcript\n", encoding="utf-8")
    out = tmp_path / "notes"

    assert main(["process-url", str(transcript), "--out", str(out)]) == 0
    [note] = list(out.glob("*.md"))
    assert "hello transcript" in note.read_text(encoding="utf-8")


def test_process_batch_writes_successes_and_failed_md(tmp_path: Path):
    transcript = tmp_path / "clip.txt"
    transcript.write_text("local transcript text", encoding="utf-8")
    links = tmp_path / "links.txt"
    links.write_text(f"{transcript}\nhttps://example.com/not-supported\n", encoding="utf-8")
    out = tmp_path / "notes"

    assert main(["process-batch", str(links), "--out", str(out)]) == 1
    notes = [p for p in out.glob("*.md") if p.name != "failed.md"]
    assert notes
    failed = out / "failed.md"
    assert failed.exists()
    failed_text = failed.read_text(encoding="utf-8")
    assert "https://example.com/not-supported" in failed_text
    assert "Unsupported source" in failed_text


def test_process_url_failure_writes_failed_md(tmp_path: Path):
    out = tmp_path / "notes"
    assert main(["process-url", "https://example.com/nope", "--out", str(out)]) == 1
    text = (out / "failed.md").read_text(encoding="utf-8")
    assert "https://example.com/nope" in text
    assert text.strip()
