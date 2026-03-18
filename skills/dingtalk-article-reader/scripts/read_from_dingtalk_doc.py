#!/usr/bin/env python3
"""
Read articles from DingTalk Docs via MCP StreamableHttp gateway.

Supported sub-commands:
  get            --endpoint URL --node-id ID_OR_URL
  search         --endpoint URL --keyword KEYWORD
  list           --endpoint URL [--folder-id ID] [--workspace-id ID]
  save-endpoint  --endpoint URL
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / ".state.json"


class StateStore:
    def __init__(self, path=DEFAULT_STATE_PATH):
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_endpoint(self) -> str:
        return self.load().get("endpoint", "")

    def set_endpoint(self, endpoint: str):
        state = self.load()
        state["endpoint"] = endpoint
        self.save(state)


class DingTalkDocReader:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.session = requests.Session()

    def _call(self, tool_name: str, arguments: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        resp = self.session.post(
            self.endpoint,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # get_document_content
    # ------------------------------------------------------------------
    def get_document_content(self, node_id: str) -> dict:
        """Fetch full Markdown content of a document by nodeId or URL."""
        # First get metadata (title, url)
        info_resp = self._call("get_document_info", {"nodeId": node_id})
        info = self._extract_json_content(info_resp)

        # Then get content
        content_resp = self._call("get_document_content", {"nodeId": node_id})
        content = self._extract_text_content(content_resp)

        return {
            "nodeId": info.get("nodeId") or info.get("dentryUuid") or node_id,
            "title": info.get("title") or info.get("name") or "",
            "url": info.get("url") or info.get("link") or "",
            "content": content,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    # ------------------------------------------------------------------
    # search_documents
    # ------------------------------------------------------------------
    def search_documents(self, keyword: str) -> list:
        """Search documents by keyword; returns list of {nodeId, title, url}."""
        resp = self._call("search_documents", {"keyword": keyword})
        items = self._extract_items(resp)
        return [
            {
                "nodeId": item.get("nodeId") or item.get("dentryUuid", ""),
                "title": item.get("title") or item.get("name", ""),
                "url": item.get("url") or item.get("link", ""),
                "contentType": item.get("contentType", ""),
                "updatedAt": item.get("updatedAt") or item.get("lastModifiedTime", ""),
            }
            for item in items
        ]

    # ------------------------------------------------------------------
    # list_nodes
    # ------------------------------------------------------------------
    def list_nodes(self, folder_id: str = None, workspace_id: str = None) -> list:
        """List nodes under a folder or workspace root."""
        args = {}
        if folder_id:
            args["folderId"] = folder_id
        if workspace_id:
            args["workspaceId"] = workspace_id

        resp = self._call("list_nodes", args)
        items = self._extract_items(resp)
        return [
            {
                "nodeId": item.get("nodeId") or item.get("dentryUuid", ""),
                "title": item.get("title") or item.get("name", ""),
                "nodeType": item.get("nodeType", ""),
                "contentType": item.get("contentType", ""),
                "url": item.get("url") or item.get("link", ""),
                "hasChildren": item.get("hasChildren", False),
            }
            for item in items
        ]

    # ------------------------------------------------------------------
    # Response parsing helpers
    # ------------------------------------------------------------------
    def _extract_json_content(self, response: dict) -> dict:
        for entry in response.get("result", {}).get("content", []):
            if entry.get("type") == "json":
                return entry.get("json", {})
        # fallback: try to parse text as JSON
        for entry in response.get("result", {}).get("content", []):
            if entry.get("type") == "text":
                try:
                    return json.loads(entry.get("text", "{}"))
                except json.JSONDecodeError:
                    pass
        return {}

    def _extract_text_content(self, response: dict) -> str:
        parts = []
        for entry in response.get("result", {}).get("content", []):
            if entry.get("type") == "text":
                parts.append(entry.get("text", ""))
            elif entry.get("type") == "json":
                data = entry.get("json", {})
                # some endpoints return markdown inside a json field
                if "markdown" in data:
                    parts.append(data["markdown"])
                elif "content" in data:
                    parts.append(data["content"])
        return "\n".join(parts).strip()

    def _extract_items(self, response: dict) -> list:
        for entry in response.get("result", {}).get("content", []):
            if entry.get("type") == "json":
                data = entry.get("json", {})
                if "items" in data:
                    return data["items"]
                if isinstance(data, list):
                    return data
        return []


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def resolve_endpoint(explicit: str = None, state_path=DEFAULT_STATE_PATH) -> str:
    """Resolve endpoint from explicit arg → env var → cached state file."""
    ep = explicit or os.environ.get("DINGTALK_DOC_MCP_ENDPOINT", "")
    if not ep:
        ep = StateStore(state_path).get_endpoint()
    if not ep:
        raise ValueError(
            "Missing MCP endpoint. Provide --endpoint, set DINGTALK_DOC_MCP_ENDPOINT, "
            "or run 'save-endpoint' first."
        )
    return ep


def cmd_get(args):
    endpoint = resolve_endpoint(args.endpoint, args.state_path)
    reader = DingTalkDocReader(endpoint)
    result = reader.get_document_content(args.node_id)
    # cache the endpoint after a successful call
    StateStore(args.state_path).set_endpoint(endpoint)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_search(args):
    endpoint = resolve_endpoint(args.endpoint, args.state_path)
    reader = DingTalkDocReader(endpoint)
    results = reader.search_documents(args.keyword)
    StateStore(args.state_path).set_endpoint(endpoint)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_list(args):
    endpoint = resolve_endpoint(args.endpoint, args.state_path)
    reader = DingTalkDocReader(endpoint)
    results = reader.list_nodes(
        folder_id=getattr(args, "folder_id", None),
        workspace_id=getattr(args, "workspace_id", None),
    )
    StateStore(args.state_path).set_endpoint(endpoint)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_save_endpoint(args):
    """Persist the endpoint URL to local state so future calls don't need --endpoint."""
    ep = args.endpoint or os.environ.get("DINGTALK_DOC_MCP_ENDPOINT", "")
    if not ep:
        print(json.dumps({"error": "--endpoint is required"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    StateStore(args.state_path).set_endpoint(ep)
    print(json.dumps({"saved": True, "endpoint": ep}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Read articles from DingTalk Docs via MCP.")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH),
                        help="Path to local state cache file (default: skill root .state.json)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # get
    p_get = subparsers.add_parser("get", help="Fetch full content of a document by ID or URL")
    p_get.add_argument("--endpoint", default=None,
                       help="MCP StreamableHttp URL (e.g. https://mcp-gw.dingtalk.com/server/...?key=...)")
    p_get.add_argument("--node-id", required=True, help="Document ID (dentryUuid) or document URL")
    p_get.set_defaults(func=cmd_get)

    # search
    p_search = subparsers.add_parser("search", help="Search documents by keyword")
    p_search.add_argument("--endpoint", default=None)
    p_search.add_argument("--keyword", required=True, help="Search keyword (matches title and content)")
    p_search.set_defaults(func=cmd_search)

    # list
    p_list = subparsers.add_parser("list", help="List nodes under a folder or workspace")
    p_list.add_argument("--endpoint", default=None)
    p_list.add_argument("--folder-id", default=None, help="Folder nodeId or URL")
    p_list.add_argument("--workspace-id", default=None, help="Workspace ID")
    p_list.set_defaults(func=cmd_list)

    # save-endpoint
    p_save = subparsers.add_parser("save-endpoint",
                                   help="Persist the MCP StreamableHttp URL to local cache")
    p_save.add_argument("--endpoint", required=True,
                        help="MCP StreamableHttp URL to cache for future use")
    p_save.set_defaults(func=cmd_save_endpoint)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
