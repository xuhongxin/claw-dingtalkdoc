from pathlib import Path
import importlib.util

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "save_to_dingtalk_doc.py"
SPEC = importlib.util.spec_from_file_location("save_to_dingtalk_doc", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_detect_language_marks_chinese_text_as_zh():
    detector = MODULE.ArticleProcessor()

    assert detector.detect_language("这是一个中文文章摘要。包含足够多的中文字符用于识别。") == "zh"


def test_detect_language_marks_english_text_as_en():
    detector = MODULE.ArticleProcessor()

    assert detector.detect_language("This is an English article summary with no Chinese characters at all.") == "en"


def test_state_store_round_trip(tmp_path):
    state_path = tmp_path / "state.json"
    store = MODULE.StateStore(state_path)

    store.save({"folder_id": "abc123", "folder_name": "OpenClawDingTalk"})

    assert store.load() == {"folder_id": "abc123", "folder_name": "OpenClawDingTalk"}


def test_render_markdown_contains_required_sections():
    rendered = MODULE.render_markdown(
        title="AI 生成标题",
        tags=["AI", "效率工具"],
        summary="这是文章概述。",
        body="这是文章正文。",
        source_url="https://example.com/post",
        source_language="zh",
        fetched_at="2026-03-16 10:00",
    )

    assert "# AI 生成标题" in rendered
    assert "## 文章分类标签" in rendered
    assert "- AI" in rendered
    assert "## 文章内容概述" in rendered
    assert "这是文章概述。" in rendered
    assert "## 文章正文" in rendered
    assert "这是文章正文。" in rendered
    assert "## 文章引用来源" in rendered
    assert "https://example.com/post" in rendered
    assert "中文" in rendered


def test_prepare_body_for_save_requires_translation_for_english_articles():
    with pytest.raises(ValueError, match="translated Chinese body"):
        MODULE.prepare_body_for_save(
            body="This is an English article body.",
            source_language="en",
        )


def test_prepare_body_for_save_uses_translated_body_for_english_articles():
    translated = MODULE.prepare_body_for_save(
        body="This is an English article body.",
        source_language="en",
        translated_body="这是一篇英文文章翻译后的中文正文。",
    )

    assert translated == "这是一篇英文文章翻译后的中文正文。"


def test_prepare_body_for_save_rejects_non_chinese_translation_for_english_articles():
    with pytest.raises(ValueError, match="must contain Chinese"):
        MODULE.prepare_body_for_save(
            body="This is an English article body.",
            source_language="en",
            translated_body="Still English content",
        )


def test_render_markdown_uses_translated_body_for_english_articles():
    rendered = MODULE.render_markdown(
        title="AI 生成标题",
        tags=["AI"],
        summary="中文概述。",
        body="This is an English article body.",
        translated_body="这是翻译后的中文正文。",
        source_url="https://example.com/post",
        source_language="en",
        fetched_at="2026-03-16 10:00",
    )

    assert "这是翻译后的中文正文。" in rendered
    assert "This is an English article body." not in rendered


def test_build_create_folder_request_uses_fixed_folder_name():
    client = MODULE.DingTalkDocClient(endpoint="https://mcp.example.com")

    request_body = client.build_create_folder_request("OpenClawDingTalk")

    assert request_body["method"] == "tools/call"
    assert request_body["params"]["name"] == "create_folder"
    assert request_body["params"]["arguments"]["name"] == "OpenClawDingTalk"


def test_build_create_document_request_targets_folder_and_markdown():
    client = MODULE.DingTalkDocClient(endpoint="https://mcp.example.com")

    request_body = client.build_create_document_request(
        title="AI 标题",
        folder_id="folder-123",
        markdown="# content",
    )

    assert request_body["method"] == "tools/call"
    assert request_body["params"]["name"] == "create_document"
    assert request_body["params"]["arguments"]["name"] == "AI 标题"
    assert request_body["params"]["arguments"]["folderId"] == "folder-123"
    assert request_body["params"]["arguments"]["markdown"] == "# content"


def test_extract_article_from_html_falls_back_to_parsed_body():
    processor = MODULE.ArticleProcessor()
    html = """
    <html>
      <head><title>Example Article</title></head>
      <body>
        <article>
          <p>First paragraph.</p>
          <p>Second paragraph.</p>
        </article>
      </body>
    </html>
    """

    article = processor.extract_from_html("https://example.com/article", html)

    assert article["title"] == "Example Article"
    assert "First paragraph." in article["content"]
    assert "Second paragraph." in article["content"]
    assert article["url"] == "https://example.com/article"


def test_extract_folder_id_from_list_nodes_response():
    client = MODULE.DingTalkDocClient(endpoint="https://mcp.example.com")
    response = {
        "result": {
            "content": [
                {
                    "type": "json",
                    "json": {
                        "items": [
                            {"nodeId": "folder-1", "title": "Other"},
                            {"nodeId": "folder-2", "title": "OpenClawDingTalk"},
                        ]
                    },
                }
            ]
        }
    }

    assert client.extract_folder_id(response, "OpenClawDingTalk") == "folder-2"


def test_ensure_target_folder_uses_cached_folder_id(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text('{"folder_id":"cached-folder","folder_name":"OpenClawDingTalk"}', encoding="utf-8")
    store = MODULE.StateStore(state_path)

    class DummyClient:
        def ensure_folder(self, folder_name):
            raise AssertionError("ensure_folder should not be called when cache exists")

    assert MODULE.ensure_target_folder(DummyClient(), store) == "cached-folder"


def test_ensure_target_folder_creates_and_persists_folder_id(tmp_path):
    state_path = tmp_path / "state.json"
    store = MODULE.StateStore(state_path)

    class DummyClient:
        def ensure_folder(self, folder_name):
            assert folder_name == "OpenClawDingTalk"
            return "new-folder-id"

    folder_id = MODULE.ensure_target_folder(DummyClient(), store)

    assert folder_id == "new-folder-id"
    assert store.load()["folder_id"] == "new-folder-id"
