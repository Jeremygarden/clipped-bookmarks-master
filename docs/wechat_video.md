# 微信视频号短视频 / 文件支持

本项目对微信视频号采用“链接识别 + 文件处理”的安全策略：视频号没有稳定公开下载 API，因此不会伪装成可直接抓取私有/受限视频。

## 支持范围

- 识别 `channels.weixin.qq.com`、`finder.video.qq.com`、`视频号` 等链接/文本提示。
- 对链接输入返回结构化 `BookmarkItem`，标记 `requires_upload=True`。
- 对用户上传/导出的本地视频文件创建可处理的 `BookmarkItem` 和 `video` asset。
- 支持扩展名：`.mp4`、`.mov`、`.m4v`、`.webm`、`.mkv`、`.avi`。

## 推荐流程

```bash
python3 - <<'PY'
from clipped_bookmarks.extractors.wechat_video import WeChatVideoExtractor
item = WeChatVideoExtractor().extract('/path/to/wechat-channel.mp4')
print(item)
PY

bash scripts/extract_audio.sh /path/to/wechat-channel.mp4
bash scripts/transcribe.sh /path/to/wechat-channel.mp3 --api openai
```

若只有视频号链接，先提示用户上传视频文件，再继续音频提取与转写。
