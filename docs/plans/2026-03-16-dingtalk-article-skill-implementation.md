# DingTalk Article Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an OpenClaw skill that saves each article as a new document inside a fixed DingTalk folder named `OpenClawDingTalk`, translating English articles into Chinese before creating structured Markdown.

**Architecture:** Create a skill package with a tested Python helper script. The helper handles extraction, local folder cache persistence, folder lookup/creation, payload generation, and DingTalk MCP writes; the skill instructions tell the agent when to invoke the helper and how to generate Chinese title, tags, summary, and translation.

**Tech Stack:** Markdown skill docs, Python 3, `requests`, `beautifulsoup4`, `pytest`

---

### Task 1: Create the failing tests

**Files:**
- Create: `skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py`
- Test: `skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py`

**Step 1: Write the failing tests**

Cover:
- detect Chinese vs English content
- persist and reload local folder cache JSON
- render Markdown with title, tags, summary, body, and source
- build DingTalk MCP `create_document` payload

**Step 2: Run test to verify it fails**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: FAIL because the implementation module does not exist yet.

**Step 3: Write minimal implementation**

Create the helper module and implement only the behavior required by the tests.

**Step 4: Run test to verify it passes**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: PASS

### Task 2: Implement article extraction and MCP append flow

**Files:**
- Create: `skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py`
- Modify: `skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py`

**Step 1: Write the failing test**

Add tests for:
- extracting title and readable text from HTML using fallback parsing
- validating the fixed folder resolution logic
- generating the outbound MCP request envelopes for folder create and document create

**Step 2: Run test to verify it fails**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: FAIL on missing extraction or validation behavior.

**Step 3: Write minimal implementation**

Implement:
- article fetch and extraction
- `OpenClawDingTalk` folder lookup/create flow
- MCP document create call wrapper

**Step 4: Run test to verify it passes**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: PASS

### Task 3: Add CLI behavior and skill docs

**Files:**
- Create: `skills/dingtalk-article-saver/SKILL.md`
- Create: `skills/dingtalk-article-saver/README.md`
- Modify: `skills/dingtalk-article-saver/scripts/save_to_dingtalk_doc.py`

**Step 1: Write the failing test**

Add tests for:
- first-run folder cache initialization path
- Markdown output mode for agent-side title/translation workflow

**Step 2: Run test to verify it fails**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: FAIL because the CLI/config behavior is incomplete.

**Step 3: Write minimal implementation**

Implement CLI flags for:
- extracting article metadata
- ensuring the target folder exists
- rendering final Markdown
- creating a DingTalk document

Write `SKILL.md` and `README.md` with exact usage guidance.

**Step 4: Run test to verify it passes**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: PASS

### Task 4: Verify behavior

**Files:**
- Verify: `skills/dingtalk-article-saver/`

**Step 1: Run automated tests**

Run: `pytest skills/dingtalk-article-saver/tests/test_save_to_dingtalk_doc.py -q`
Expected: PASS

**Step 2: Run a manual smoke check**

Run extraction mode against sample HTML or a safe article URL.
Expected: JSON or Markdown output with the required sections.

**Step 3: Review docs**

Check that `SKILL.md` accurately describes:
- automatic `OpenClawDingTalk` folder creation
- translation rule for English articles
- AI-generated title rule
- required final Markdown structure

**Step 4: Commit**

This repository is not currently a git repository, so no commit step can be executed here.
