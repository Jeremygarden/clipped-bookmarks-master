from pathlib import Path

from clipped_bookmarks.kb import ensure_kb_layout, process_batch, write_item_note
from clipped_bookmarks.schema import BookmarkItem, Platform, SourceType


def test_ensure_kb_layout_creates_required_files_and_dirs(tmp_path: Path):
    ensure_kb_layout(tmp_path)
    for name in ["index.md", "failed.md"]:
        assert (tmp_path / name).is_file()
    for name in ["sources", "weixin", "zhihu", "xiaohongshu", "topics", "batches", "assets"]:
        assert (tmp_path / name).is_dir()


def test_write_item_note_uses_platform_directory(tmp_path: Path):
    item = BookmarkItem(
        url="https://zhuanlan.zhihu.com/p/123",
        platform=Platform.ZHIHU,
        source_type=SourceType.ZHIHU_ARTICLE,
        title="A Zhihu Note",
    )
    path = write_item_note(item, tmp_path)
    assert path.parent == tmp_path / "zhihu"
    assert path.read_text(encoding="utf-8").startswith("---")


def test_process_batch_writes_summary_success_failure_and_all_notes(tmp_path: Path):
    links = [
        "https://zhuanlan.zhihu.com/p/123",
        "https://mp.weixin.qq.com/s/abc",
        "https://example.com/not-supported",
    ]
    result = process_batch(links, tmp_path, batch_id="batch-test")
    assert len(result.successes) == 2
    assert len(result.failures) == 1
    summary = (tmp_path / "batches" / "batch-test.md").read_text(encoding="utf-8")
    assert "## Success List" in summary
    assert "## Failure List" in summary
    assert "## All Notes Index" in summary
    assert "zhihu/" in summary
    assert "weixin/" in summary
    assert "example.com/not-supported" in (tmp_path / "failed.md").read_text(encoding="utf-8")
    assert "## All Notes" in (tmp_path / "index.md").read_text(encoding="utf-8")
