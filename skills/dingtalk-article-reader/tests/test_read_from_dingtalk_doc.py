"""Unit tests for DingTalkDocReader and StateStore (no real network calls)."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub `requests` so the module can be imported without the package installed
# ---------------------------------------------------------------------------
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _Session:
        def post(self, *a, **kw):
            pass

    requests_stub.Session = _Session
    sys.modules["requests"] = requests_stub

import importlib

_script = Path(__file__).resolve().parents[1] / "scripts" / "read_from_dingtalk_doc.py"
spec = importlib.util.spec_from_file_location("read_from_dingtalk_doc", _script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
DingTalkDocReader = mod.DingTalkDocReader
StateStore = mod.StateStore
resolve_endpoint = mod.resolve_endpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_json_response(data: dict) -> dict:
    return {"result": {"content": [{"type": "json", "json": data}]}}


def _make_text_response(text: str) -> dict:
    return {"result": {"content": [{"type": "text", "text": text}]}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractHelpers(unittest.TestCase):
    def setUp(self):
        self.reader = DingTalkDocReader.__new__(DingTalkDocReader)

    def test_extract_json_content(self):
        resp = _make_json_response({"title": "Hello", "nodeId": "abc123"})
        result = self.reader._extract_json_content(resp)
        self.assertEqual(result["title"], "Hello")

    def test_extract_text_content(self):
        resp = _make_text_response("# My Doc\n\nSome content")
        result = self.reader._extract_text_content(resp)
        self.assertIn("My Doc", result)

    def test_extract_items(self):
        resp = _make_json_response({"items": [{"nodeId": "n1", "title": "Doc A"}]})
        items = self.reader._extract_items(resp)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Doc A")

    def test_extract_items_empty(self):
        resp = {"result": {"content": []}}
        self.assertEqual(self.reader._extract_items(resp), [])


class TestGetDocumentContent(unittest.TestCase):
    def _make_reader(self):
        reader = DingTalkDocReader.__new__(DingTalkDocReader)
        reader.endpoint = "https://fake-endpoint"
        reader.session = MagicMock()
        return reader

    def test_get_document_content_success(self):
        reader = self._make_reader()
        info_resp = _make_json_response({"nodeId": "abc", "title": "Test Doc", "url": "https://alidocs.dingtalk.com/i/nodes/abc"})
        content_resp = _make_text_response("# Test Doc\n\nHello world")

        call_results = [info_resp, content_resp]
        reader._call = MagicMock(side_effect=call_results)

        result = reader.get_document_content("abc")
        self.assertEqual(result["title"], "Test Doc")
        self.assertIn("Hello world", result["content"])
        self.assertEqual(result["nodeId"], "abc")

    def test_get_document_content_uses_node_id_fallback(self):
        reader = self._make_reader()
        # info returns no nodeId
        info_resp = _make_json_response({"title": "Fallback Doc"})
        content_resp = _make_text_response("content here")
        reader._call = MagicMock(side_effect=[info_resp, content_resp])

        result = reader.get_document_content("my-node-id")
        self.assertEqual(result["nodeId"], "my-node-id")


class TestSearchDocuments(unittest.TestCase):
    def test_search_returns_list(self):
        reader = DingTalkDocReader.__new__(DingTalkDocReader)
        reader.endpoint = "https://fake"
        reader._call = MagicMock(return_value=_make_json_response({
            "items": [
                {"nodeId": "n1", "title": "Article A", "url": "https://alidocs.dingtalk.com/i/nodes/n1", "contentType": "alidoc"},
                {"nodeId": "n2", "title": "Article B", "url": "https://alidocs.dingtalk.com/i/nodes/n2", "contentType": "alidoc"},
            ]
        }))
        results = reader.search_documents("Article")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Article A")

    def test_search_empty_result(self):
        reader = DingTalkDocReader.__new__(DingTalkDocReader)
        reader._call = MagicMock(return_value=_make_json_response({"items": []}))
        self.assertEqual(reader.search_documents("nothing"), [])


class TestListNodes(unittest.TestCase):
    def test_list_nodes_with_folder(self):
        reader = DingTalkDocReader.__new__(DingTalkDocReader)
        reader._call = MagicMock(return_value=_make_json_response({
            "items": [
                {"nodeId": "f1", "title": "Subfolder", "nodeType": "folder", "hasChildren": True},
                {"nodeId": "d1", "title": "Doc 1", "nodeType": "file", "contentType": "alidoc"},
            ]
        }))
        results = reader.list_nodes(folder_id="parent-folder")
        reader._call.assert_called_once_with("list_nodes", {"folderId": "parent-folder"})
        self.assertEqual(len(results), 2)

    def test_list_nodes_root(self):
        reader = DingTalkDocReader.__new__(DingTalkDocReader)
        reader._call = MagicMock(return_value=_make_json_response({"items": []}))
        reader.list_nodes()
        reader._call.assert_called_once_with("list_nodes", {})


class TestStateStore(unittest.TestCase):
    def test_set_and_get_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".state.json"
            store = StateStore(state_path)
            self.assertEqual(store.get_endpoint(), "")
            store.set_endpoint("https://mcp-gw.dingtalk.com/server/abc?key=xyz")
            self.assertEqual(store.get_endpoint(), "https://mcp-gw.dingtalk.com/server/abc?key=xyz")

    def test_set_endpoint_preserves_other_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".state.json"
            store = StateStore(state_path)
            store.save({"other_key": "other_value"})
            store.set_endpoint("https://mcp-gw.dingtalk.com/server/abc?key=xyz")
            state = store.load()
            self.assertEqual(state["other_key"], "other_value")
            self.assertEqual(state["endpoint"], "https://mcp-gw.dingtalk.com/server/abc?key=xyz")

    def test_load_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "nonexistent.json")
            self.assertEqual(store.load(), {})


class TestResolveEndpoint(unittest.TestCase):
    def test_explicit_arg_wins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ep = resolve_endpoint("https://explicit-url", Path(tmpdir) / ".state.json")
            self.assertEqual(ep, "https://explicit-url")

    def test_falls_back_to_state_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".state.json"
            StateStore(state_path).set_endpoint("https://cached-url")
            ep = resolve_endpoint(None, state_path)
            self.assertEqual(ep, "https://cached-url")

    def test_raises_when_nothing_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            env_backup = os.environ.pop("DINGTALK_DOC_MCP_ENDPOINT", None)
            try:
                with self.assertRaises(ValueError):
                    resolve_endpoint(None, Path(tmpdir) / ".state.json")
            finally:
                if env_backup is not None:
                    os.environ["DINGTALK_DOC_MCP_ENDPOINT"] = env_backup


if __name__ == "__main__":
    unittest.main()
