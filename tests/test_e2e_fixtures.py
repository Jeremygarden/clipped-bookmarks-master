from pathlib import Path

import pytest

from clipped_bookmarks.process_url import process_source

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("fixture", "snapshot"),
    [
        ("fixtures/weixin_article.html", "expected/weixin_article.md"),
        ("fixtures/zhihu_answer.html", "expected/zhihu_answer.md"),
        ("fixtures/transcript.txt", "expected/transcript.md"),
    ],
)
def test_fixture_renders_expected_markdown(fixture, snapshot):
    assert process_source(str(ROOT / fixture)) == (ROOT / snapshot).read_text(encoding="utf-8")


def test_failure_path_writes_failed_markdown(tmp_path):
    failed = tmp_path / "failed.md"
    with pytest.raises(FileNotFoundError):
        process_source(str(tmp_path / "missing.html"), failed_path=failed)
    assert failed.exists()
    assert "# Failed" in failed.read_text(encoding="utf-8")
    assert "FileNotFoundError" in failed.read_text(encoding="utf-8")
