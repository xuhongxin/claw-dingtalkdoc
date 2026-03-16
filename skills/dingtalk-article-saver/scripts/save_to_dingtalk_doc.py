#!/usr/bin/env python3

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


FIXED_FOLDER_NAME = "OpenClawDingTalk"
DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / ".state.json"


class StateStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ArticleProcessor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
            }
        )

    def detect_language(self, text):
        sample = text.strip()
        if not sample:
            return "unknown"
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", sample))
        return "zh" if chinese_chars / max(len(sample), 1) > 0.1 else "en"

    def extract_from_html(self, url, html):
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string or "").strip() if soup.title and soup.title.string else "Untitled"
        content = self._extract_text(soup)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        return {"title": title, "content": content, "url": url, "language": self.detect_language(content)}

    def fetch_article(self, url):
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return self.extract_from_html(url, response.text)

    def _extract_text(self, soup):
        preferred = soup.find("article") or soup.find("main") or soup.body or soup
        texts = []
        for node in preferred.find_all(["h1", "h2", "h3", "p", "li"]):
            text = node.get_text(" ", strip=True)
            if text:
                texts.append(text)
        if texts:
            return "\n\n".join(texts)
        return preferred.get_text("\n", strip=True)


class DingTalkDocClient:
    def __init__(self, endpoint, session=None):
        self.endpoint = endpoint
        self.session = session or requests.Session()

    def build_create_folder_request(self, folder_name):
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_folder", "arguments": {"name": folder_name}},
        }

    def build_list_nodes_request(self):
        return {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_nodes", "arguments": {}}}

    def build_create_document_request(self, title, folder_id, markdown):
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_document",
                "arguments": {"name": title, "folderId": folder_id, "markdown": markdown},
            },
        }

    def call(self, payload):
        response = self.session.post(
            self.endpoint,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def extract_folder_id(self, response, folder_name):
        items = []
        for entry in response.get("result", {}).get("content", []):
            if entry.get("type") == "json":
                items.extend(entry.get("json", {}).get("items", []))
        for item in items:
            if item.get("title") == folder_name or item.get("name") == folder_name:
                return item.get("nodeId")
        return None

    def extract_created_folder_id(self, response):
        for entry in response.get("result", {}).get("content", []):
            if entry.get("type") == "json":
                data = entry.get("json", {})
                return data.get("nodeId") or data.get("id")
        return None

    def ensure_folder(self, folder_name=FIXED_FOLDER_NAME):
        listed = self.call(self.build_list_nodes_request())
        folder_id = self.extract_folder_id(listed, folder_name)
        if folder_id:
            return folder_id
        created = self.call(self.build_create_folder_request(folder_name))
        folder_id = self.extract_created_folder_id(created)
        if not folder_id:
            raise RuntimeError(f"Failed to create folder: {folder_name}")
        return folder_id

    def create_document(self, title, folder_id, markdown):
        return self.call(self.build_create_document_request(title, folder_id, markdown))


def render_markdown(title, tags, summary, body, source_url, source_language, fetched_at):
    tag_lines = "\n".join(f"- {tag}" for tag in tags)
    language_label = {"zh": "中文", "en": "英文"}.get(source_language, source_language)
    return f"""# {title}

## 文章分类标签
{tag_lines}

## 文章内容概述
{summary}

## 文章正文
{body}

## 文章引用来源
- 原始链接: {source_url}
- 抓取时间: {fetched_at}
- 原文语言: {language_label}
"""


def ensure_target_folder(client, store, folder_name=FIXED_FOLDER_NAME):
    state = store.load()
    cached_folder_id = state.get("folder_id")
    if cached_folder_id:
        return cached_folder_id
    folder_id = client.ensure_folder(folder_name)
    store.save({"folder_id": folder_id, "folder_name": folder_name})
    return folder_id


def resolve_endpoint(explicit_endpoint=None):
    endpoint = explicit_endpoint or os.environ.get("DINGTALK_DOC_MCP_ENDPOINT")
    if not endpoint:
        raise ValueError("Missing MCP endpoint. Provide --endpoint or set DINGTALK_DOC_MCP_ENDPOINT.")
    return endpoint


def extract_command(args):
    processor = ArticleProcessor()
    article = processor.fetch_article(args.url)
    print(json.dumps(article, ensure_ascii=False, indent=2))


def save_command(args):
    client = DingTalkDocClient(resolve_endpoint(args.endpoint))
    store = StateStore(args.state_path)
    folder_id = ensure_target_folder(client, store)
    response = client.create_document(args.title, folder_id, args.markdown)
    print(json.dumps(response, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Save article content into DingTalk docs.")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("url")
    extract_parser.set_defaults(func=extract_command)

    save_parser = subparsers.add_parser("save")
    save_parser.add_argument("--endpoint", required=True)
    save_parser.add_argument("--title", required=True)
    save_parser.add_argument("--markdown", required=True)
    save_parser.set_defaults(func=save_command)

    args = parser.parse_args()
    args.fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    args.func(args)


if __name__ == "__main__":
    main()
