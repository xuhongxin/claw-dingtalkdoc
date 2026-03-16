# dingtalk-article-saver

OpenClaw skill for saving web articles into DingTalk Docs.

## Behavior

- Extracts readable text from a URL
- Detects source language
- Lets the agent generate a Chinese title, Chinese summary, Chinese tags
- Requires English articles to be translated into Chinese before saving
- Ensures a fixed folder named `OpenClawDingTalk` exists
- Creates one DingTalk document per article

## Files

- `SKILL.md`: trigger and workflow instructions
- `scripts/save_to_dingtalk_doc.py`: extraction and DingTalk persistence helper
- `tests/test_save_to_dingtalk_doc.py`: unit tests

## Environment

Set:

```bash
export DINGTALK_DOC_MCP_ENDPOINT='https://mcp-gw.dingtalk.com/server/...'
```

Dependencies:

```bash
pip3 install requests beautifulsoup4 pytest
```

## Usage

Extract article content:

```bash
python3 skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py extract "https://example.com/post"
```

Save a prepared Markdown document:

```bash
python3 skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py save \
  --title "AI 生成的标题" \
  --markdown "# AI 生成的标题\n\n## 文章分类标签\n- AI"
```

## Notes

- The helper caches the DingTalk folder id in `skills/dingtalk-article-saver/.state.json`.
- The MCP endpoint is intentionally externalized via environment variable instead of being committed into the repository.
