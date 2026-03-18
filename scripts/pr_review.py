#!/usr/bin/env python3
"""Claude PR review — posts a code review comment on PRs to main."""

import json
import os
import sys
import urllib.request
import urllib.error

import anthropic

SYSTEM_PROMPT = """You are a code reviewer for YourWriter, an AI writing platform.

Stack: Python 3.11 / FastAPI / SQLAlchemy async (aiosqlite + asyncpg) / React 19 / TypeScript / LangGraph.

Review the diff for issues in these categories:

🔴 CRITICAL — must fix before merging:
- Auth bypass or missing ownership checks (e.g. user can access another user's writer)
- SQL injection or XSS
- Data loss (destructive migrations, missing cascade, lost writes)
- Breaking API contract changes without coordinated frontend update
- SQLite session held open during LLM/streaming calls (blocks all writes for 10-30s)

🟡 WARNING — worth addressing but not blocking:
- Missing error handling on external calls (Anthropic API, web search)
- N+1 queries or unnecessary DB round-trips
- Hardcoded secrets or env vars that should come from config
- React state mutation instead of immutable update

🔵 INFO — optional, low priority:
- Style or naming inconsistencies
- Minor improvements

Format your response exactly like this:

## PR Review

**Summary:** [1-2 sentences describing what the PR does]

**Issues:**
[List each issue with its emoji prefix, or write "No issues found." if clean]

**Verdict:** APPROVED | NEEDS_WORK
"""

MAX_DIFF_CHARS = 30_000


def github_request(url: str, token: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def post_comment(repo: str, pr_number: int, token: str, body: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    urllib.request.urlopen(req)


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    api_key = os.environ["ANTHROPIC_API_KEY"]
    repo = os.environ["GITHUB_REPOSITORY"]

    # PR number from event payload
    event_path = os.environ["GITHUB_EVENT_PATH"]
    with open(event_path) as f:
        event = json.load(f)
    pr_number: int = event["pull_request"]["number"]

    print(f"Reviewing PR #{pr_number} in {repo}")

    # Fetch diff
    diff_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    raw_diff = github_request(diff_url, token, accept="application/vnd.github.v3.diff").decode("utf-8")

    if not raw_diff.strip():
        print("Empty diff — skipping review.")
        return

    if len(raw_diff) > MAX_DIFF_CHARS:
        raw_diff = raw_diff[:MAX_DIFF_CHARS] + f"\n\n[diff truncated at {MAX_DIFF_CHARS} chars]"

    # Call Claude
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"```diff\n{raw_diff}\n```"}],
    )
    review = response.content[0].text

    # Post comment
    comment = f"<!-- claude-pr-review -->\n{review}\n\n---\n*🤖 Automated review by Claude Sonnet 4.6*"
    post_comment(repo, pr_number, token, comment)
    print("Review posted.")

    # Fail the check if CRITICAL issues found
    if "🔴 CRITICAL" in review:
        print("CRITICAL issues detected — failing check.")
        sys.exit(1)


if __name__ == "__main__":
    main()
