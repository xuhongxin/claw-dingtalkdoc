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

## Configuration

Do not ask the user to run an `export` command after skill installation.

When a save action actually needs DingTalk Docs access and the current conversation does not yet contain a usable MCP StreamableHttp URL, prompt the user with:

```text
1. 登录：https://mcp.dingtalk.com/
2. 点击“钉钉文档”
3. 复制 StreamableHttp URL
4. 粘贴到当前对话；完成配置
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
  --endpoint "https://mcp-gw.dingtalk.com/server/..." \
  --title "AI 生成的标题" \
  --markdown "# AI 生成的标题\n\n## 文章分类标签\n- AI"
```

## Notes

- The helper caches the DingTalk folder id in `skills/dingtalk-article-saver/.state.json`.
- The MCP endpoint should be collected from the user during the save flow instead of being preconfigured during installation.
