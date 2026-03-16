## DingTalk Article Skill Design

### Goal

Build an OpenClaw skill that accepts an article URL, extracts readable content, translates English articles into Chinese, generates an AI title, tags, and a summary, then creates a new DingTalk document under a fixed folder named `OpenClawDingTalk`.

### Constraints

- The target folder is fixed to `OpenClawDingTalk`.
- If the folder does not exist, the skill must create it automatically.
- Each article must be saved as a separate DingTalk document.
- The document title must be determined by AI based on the article content, with webpage title as a fallback.
- The DingTalk writing path uses the existing MCP endpoint already provided by the user, but the endpoint itself should not be hardcoded into source control.
- Output format must contain:
  - Article category tags
  - Article summary
  - Article body
  - Source citation
- The solution should be usable as an OpenClaw skill package, not only as a standalone script.
- The current repository is empty, so the skill package structure needs to be created from scratch.

### Recommended Approach

Use a lightweight skill package with:

- `SKILL.md` for trigger conditions and operating rules
- One Python helper module for fetch, extraction, language detection, folder lookup/creation, and MCP writes
- One CLI entry script used by the skill instructions
- Unit tests for deterministic logic

This keeps the skill simple enough for OpenClaw, while pushing brittle steps such as HTML extraction and DingTalk MCP calls into code that can be tested.

### Alternatives Considered

1. Pure SKILL-only implementation
   - Pros: minimal code
   - Cons: poor repeatability, no folder reuse logic, weak error handling

2. Direct shell script with `curl` and text processing
   - Pros: low dependency footprint
   - Cons: fragile extraction and formatting, difficult testing

3. Skill plus Python helper scripts
   - Pros: best balance of reliability, readability, testing, and future extension
   - Cons: slightly more implementation work

Chosen: option 3.

### Architecture

The skill will be composed of four layers:

1. Skill interface
   - Declares when the skill should trigger
   - Tells the agent to call the helper CLI for extraction and persistence
   - Explains the required output sections

2. Content processing
   - Fetch article HTML
   - Extract title and readable text using a readability-first, BeautifulSoup fallback strategy
   - Detect whether the article is mostly Chinese or mostly non-Chinese

3. Content packaging
   - Preserve Chinese content as-is
   - Mark English content as requiring translation by the agent, while also allowing an optional direct input path for translated text
   - Generate a Markdown payload with fixed sections for tags, summary, body, and source

4. DingTalk persistence
   - Read local state from a JSON file to cache the resolved folder ID
   - Look up `OpenClawDingTalk`; create it if missing
   - Create one new DingTalk document per article using `create_document`

### Data Flow

1. User provides article URL.
2. Helper extracts article title, text, and detected language.
3. Skill checks local state for cached DingTalk folder ID.
4. If missing or invalid, helper locates or creates `OpenClawDingTalk`.
5. Agent generates:
   - Chinese document title
   - Chinese translation if source is English
   - Chinese summary
   - Chinese tags
6. Helper or agent assembles final Markdown payload.
7. Helper calls the DingTalk MCP endpoint and creates a new document under the target folder.

### File Layout

- `skills/dingtalk-article-saver/SKILL.md`
- `skills/dingtalk-article-saver/README.md`
- `skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py`
- `skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py`
- `docs/plans/2026-03-16-dingtalk-article-skill-design.md`
- `docs/plans/2026-03-16-dingtalk-article-skill-implementation.md`

### Error Handling

- Unreachable article URL: fail with a clear fetch error.
- Empty extraction result: fail with an extraction error instead of writing an empty document.
- Missing cached folder ID: search the fixed folder by name and create it if needed.
- Invalid cached folder ID: fall back to folder lookup and refresh the cache.
- MCP write failure: surface endpoint response details and keep generated Markdown in stdout for recovery.

### Testing Strategy

Use unit tests for:

- language detection
- sectioned Markdown rendering
- cache file load/save behavior
- folder search/create request payload generation
- extraction fallback behavior with sample HTML

Networked end-to-end tests will be manual because the environment does not provide a stable test fixture for external web pages or live DingTalk documents.
