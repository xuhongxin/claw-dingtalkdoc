# dingtalk-article-reader

OpenClaw skill for reading articles from DingTalk Docs and returning content to the host agent for analysis.

## Behavior

- Supports three lookup modes: by document ID/URL, by keyword search, or by browsing a folder/workspace
- Returns full Markdown content of the target document
- Hands the content back to the host agent for downstream tasks (summarization, translation, Q&A, etc.)

## Files

- `SKILL.md`: trigger conditions and workflow instructions for the agent
- `scripts/read_from_dingtalk_doc.py`: MCP client for reading DingTalk Docs
- `tests/test_read_from_dingtalk_doc.py`: unit tests (no network required)

## Configuration

Do not ask the user to run an `export` command after skill installation.

When a read action actually needs DingTalk Docs access and the current conversation does not yet contain a usable MCP StreamableHttp URL, prompt the user with:

```text
1. 登录：https://mcp.dingtalk.com/
2. 点击"钉钉文档"
3. 复制 StreamableHttp URL
4. 粘贴到当前对话；完成配置
```

Dependencies:

```bash
pip3 install requests pytest
```

## Usage

Fetch a document by ID or URL:

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py get \
  --endpoint "https://mcp-gw.dingtalk.com/server/..." \
  --node-id "abc123def456"
```

Search by keyword:

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py search \
  --endpoint "https://mcp-gw.dingtalk.com/server/..." \
  --keyword "季度总结"
```

List nodes under a folder:

```bash
python3 skills/dingtalk-article-reader/scripts/read_from_dingtalk_doc.py list \
  --endpoint "https://mcp-gw.dingtalk.com/server/..." \
  --folder-id "folder-node-id"
```

## Output

All commands output JSON to stdout. The `get` command returns:

```json
{
  "nodeId": "abc123",
  "title": "文档标题",
  "url": "https://alidocs.dingtalk.com/i/nodes/abc123",
  "content": "# 文档标题\n\n正文内容...",
  "fetched_at": "2024-01-01 12:00"
}
```

The `content` field is the full Markdown body, ready for the host agent to analyze.

## Notes

- `get_document_content` only supports DingTalk online documents (`contentType=alidoc`). PDF, docx, and other file types are not supported.
- The MCP endpoint URL should be collected from the user during the read flow, not preconfigured at install time.
- Set `DINGTALK_DOC_MCP_ENDPOINT` environment variable as an alternative to passing `--endpoint` each time.
