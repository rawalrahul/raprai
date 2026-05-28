"""
helm/learning/index_updater.py — Auto-generates LEARNING_INDEX.md from live metrics.
Called weekly or on-demand.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

_INDEX_PATH = Path(__file__).parent / "LEARNING_INDEX.md"
_ANALYZER_OUTPUT_DIR = Path(__file__).parent / "analyzer_output"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _pct(f: float) -> str:
    return f"{f * 100:.1f}%"


def _cost(f: float) -> str:
    return f"${f:.4f}"


def _recent_improvements() -> str:
    """
    Collect last 7 days of analyzer output lines, if any exist.
    Looks for files in helm/learning/analyzer_output/ modified in last 7 days.
    Returns a markdown-formatted string.
    """
    try:
        if not _ANALYZER_OUTPUT_DIR.exists():
            return "*(no analyzer output found)*"

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        lines = []
        for f in sorted(_ANALYZER_OUTPUT_DIR.iterdir()):
            if not f.is_file():
                continue
            try:
                import os
                mtime = datetime.fromtimestamp(os.path.getmtime(f), tz=timezone.utc)
                if mtime < cutoff:
                    continue
                with f.open("r", encoding="utf-8") as fh:
                    content = fh.read(2000)  # cap per file
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        lines.append(f"- {line}")
                if len(lines) >= 20:
                    break
            except Exception:
                continue

        return "\n".join(lines) if lines else "*(no recent analyzer output)*"
    except Exception:
        return "*(error reading analyzer output)*"


def _determine_phase(summary: dict, routing: dict) -> tuple[int, str]:
    """Heuristic: determine current phase number and status line."""
    total = summary.get("total_tasks", 0)
    tracked = routing.get("task_types_tracked", 0)
    recs = routing.get("routing_recommendations", [])
    high_conf = [r for r in recs if r.get("confidence", 0) >= 0.8 and r.get("sample_count", 0) >= 15]

    if high_conf:
        return 3, "routing recommendations ready for promotion"
    if tracked > 0 and total >= 10:
        return 2, "shadow routing active, accumulating confidence"
    return 1, "collecting data, shadow mode active"


def update_learning_index() -> None:
    """Regenerate LEARNING_INDEX.md with current stats. Never raises."""
    try:
        from helm.learning import metrics
    except ImportError:
        try:
            import importlib
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from helm.learning import metrics  # type: ignore
        except Exception:
            # Last resort: direct relative import
            try:
                from . import metrics  # type: ignore
            except Exception:
                return

    try:
        summary = metrics.get_summary(days=30)
        routing = metrics.get_routing_summary()
        playbooks = metrics.get_playbook_stats()
        proposals = metrics.get_proposal_stats()

        phase_num, status_line = _determine_phase(summary, routing)
        now_str = _iso_now()

        # ---------------------------------------------------------------
        # Section: AI Performance Comparison
        # ---------------------------------------------------------------
        ai_rows = []
        tasks_by_ai = summary.get("tasks_by_ai", {})
        for ai in sorted(tasks_by_ai.keys()):
            count = tasks_by_ai[ai]
            sr = summary.get("success_rate_by_ai", {}).get(ai, 0.0)
            dur = summary.get("avg_duration_by_ai", {}).get(ai, 0.0)
            cost_total = summary.get("cost_by_ai", {}).get(ai, 0.0)
            avg_cost = cost_total / count if count else 0.0
            ai_rows.append(
                f"| {ai} | {count} | {_pct(sr)} | {dur:.0f}s | {_cost(avg_cost)} |"
            )

        if ai_rows:
            ai_table = (
                "| AI | Tasks | Success Rate | Avg Duration | Avg Cost |\n"
                "|---|---|---|---|---|\n"
                + "\n".join(ai_rows)
            )
        else:
            ai_table = "*No AI performance data yet.*"

        # ---------------------------------------------------------------
        # Section: Routing Recommendations
        # ---------------------------------------------------------------
        recs = routing.get("routing_recommendations", [])
        shadow_label = " (Shadow Mode)" if routing.get("shadow_mode", True) else ""
        if recs:
            rec_rows = [
                f"| {r['task_type']} | {r['best_ai']} | {_pct(r['confidence'])} | {r['sample_count']} |"
                for r in recs
            ]
            routing_table = (
                "| Task Type | Recommended AI | Confidence | Samples |\n"
                "|---|---|---|---|\n"
                + "\n".join(rec_rows)
            )
        else:
            routing_table = "*No routing recommendations yet — need 5+ samples per task type.*"

        # ---------------------------------------------------------------
        # Section: Top Playbooks
        # ---------------------------------------------------------------
        top = playbooks.get("top_playbooks", [])[:5]
        if top:
            pb_lines = [
                f"- **{p['name']}** ({p['task_type']}) — "
                f"success rate {_pct(p['success_rate'])}, {p['sample_count']} samples"
                for p in top
            ]
            top_pb_section = "\n".join(pb_lines)
        else:
            top_pb_section = "*No playbooks recorded yet.*"

        # ---------------------------------------------------------------
        # Section: Proposals
        # ---------------------------------------------------------------
        pending = proposals.get("pending", 0)
        total_props = proposals.get("total", 0)
        if total_props == 0:
            proposals_line = "*No skill proposals on record.*"
        elif pending == 0:
            proposals_line = f"{total_props} total proposals — none pending review."
        else:
            proposals_line = (
                f"{pending} proposal{'s' if pending != 1 else ''} pending review "
                f"({total_props} total) — visit `/learning/proposals` to review."
            )

        # ---------------------------------------------------------------
        # Section: Recent Improvements
        # ---------------------------------------------------------------
        recent = _recent_improvements()

        # ---------------------------------------------------------------
        # Assemble markdown
        # ---------------------------------------------------------------
        total_tasks = summary.get("total_tasks", 0)
        sr_pct = _pct(summary.get("success_rate", 0.0))
        avg_dur = summary.get("avg_duration_seconds", 0.0)
        total_cost = summary.get("total_cost_usd", 0.0)

        pb_active = playbooks.get("active", 0)
        pb_draft = playbooks.get("draft", 0)
        pb_deprecated = playbooks.get("deprecated", 0)

        md = f"""# Learning Index — Helm HQ Self-Improvement

**Last updated:** {now_str}
**Status:** Phase {phase_num} — {status_line}

## Summary (Last 30 Days)
- Total tasks logged: {total_tasks}
- Overall success rate: {sr_pct}
- Average task duration: {avg_dur:.1f}s
- Total API cost: {_cost(total_cost)}

## AI Performance Comparison{shadow_label}

{ai_table}

## Routing Recommendations{shadow_label}

{routing_table}

## Playbooks

- Active: {pb_active} | Draft: {pb_draft} | Deprecated: {pb_deprecated}

### Top Performing Playbooks
{top_pb_section}

## Pending Skill Proposals
{proposals_line}

## Recent Improvements
{recent}

---
*Auto-generated by Helm HQ self-improvement system*
"""

        _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _INDEX_PATH.open("w", encoding="utf-8") as fh:
            fh.write(md)

    except Exception:
        # Silent failure — never propagate
        pass
