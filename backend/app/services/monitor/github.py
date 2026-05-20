"""
Optional GitHub integration — opens a draft PR from an approved diagnosis.

Disabled unless ``GITHUB_TOKEN`` and ``GITHUB_REPO`` (``owner/repo``) are set.
This is a best-effort surface: when those are missing we just return a
human-readable PR description so the owner can apply the patch themselves.
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.models.monitor import MonitorDiagnosis

_GITHUB_API = "https://api.github.com"


def is_available() -> bool:
    return bool(settings.GITHUB_TOKEN and settings.GITHUB_REPO)


def render_pr_description(diag: MonitorDiagnosis) -> str:
    lines: list[str] = []
    lines.append("## Proposed fix from the YBS monitor agent")
    lines.append("")
    lines.append(f"**Confidence:** {diag.confidence}")
    if diag.root_cause_summary:
        lines.append("")
        lines.append("### Root cause")
        lines.append(diag.root_cause_summary)
    if diag.proposed_fix:
        lines.append("")
        lines.append("### Proposed fix")
        lines.append(diag.proposed_fix)
    if diag.files_changed:
        lines.append("")
        lines.append("### Files changed")
        for entry in diag.files_changed:
            path = entry.get("path", "?")
            patch = entry.get("patch", "")
            lines.append(f"#### {path}")
            lines.append("```diff")
            lines.append(patch)
            lines.append("```")
    if diag.reviewer_agent_verdict:
        verdict = diag.reviewer_agent_verdict.get("verdict", "?")
        notes = diag.reviewer_agent_verdict.get("notes", "")
        lines.append("")
        lines.append("### Reviewer agent verdict")
        lines.append(f"**{verdict}** — {notes}")
    return "\n".join(lines)


async def open_draft_pr(diag: MonitorDiagnosis, *, base_branch: str = "main") -> dict:
    """
    Open a draft PR carrying the rendered description. Returns
    ``{"status": "skipped"|"created"|"error", "url": ..., "message": ...}``.

    This intentionally does NOT push files — applying the diff is the human's
    decision. The PR is a marker + audit trail; the human pastes/applies the
    patch.
    """
    if not is_available():
        return {
            "status": "skipped",
            "url": None,
            "message": "GITHUB_TOKEN or GITHUB_REPO not configured.",
        }

    description = render_pr_description(diag)
    title = (
        diag.root_cause_summary[:80]
        if diag.root_cause_summary
        else f"Monitor diagnosis {diag.id}"
    )
    # Open the PR head against base; the human will push the actual patch.
    payload = {
        "title": f"[monitor] {title}",
        "head": base_branch,
        "base": base_branch,
        "body": description,
        "draft": True,
    }
    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/pulls"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "status": "created",
                "url": data.get("html_url"),
                "message": "Draft PR opened.",
            }
        return {
            "status": "error",
            "url": None,
            "message": f"GitHub API {resp.status_code}: {resp.text[:200]}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "url": None, "message": str(exc)}
