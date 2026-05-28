"""
helm/learning/cli.py — Export / import / rollback / snapshot CLI.

Usage (run from repo root):
    python -m helm.learning.cli <command> [args]

Commands:
    export   <output_path>               Build learning_bundle.tar.gz
    import   <bundle_path>               Merge bundle into current store
    rollback playbook <name>             Relink playbook to previous version
    rollback routing  [--days N]         Restore routing table from N-day-old snapshot
    rollback skill    <skill_path>       Restore skill file from backup
    snapshot                             Write routing table snapshot to routing_history/
    status                               Print learning system status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_ROUTING_TABLE = _HERE / "routing_table.json"
_ROUTING_HISTORY = _HERE / "routing_history"
_PLAYBOOKS_DIR = _HERE / "playbooks"
_ANTIPATTERNS_DIR = _HERE / "antipatterns"
_USER_CONTEXT = _HERE / "user_context.json"
_SKILL_BACKUPS = _HERE / "skill_backups"
_CONFLICTS_LOG = _HERE / "import_conflicts.log"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_conflict(msg: str) -> None:
    _CONFLICTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _CONFLICTS_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{_now_iso()} {msg}\n")


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def cmd_snapshot(_args: argparse.Namespace) -> int:
    """Write current routing_table.json to routing_history/."""
    if not _ROUTING_TABLE.exists():
        print("ERROR: routing_table.json not found")
        return 1
    _ROUTING_HISTORY.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    dest = _ROUTING_HISTORY / f"{stamp}.json"
    shutil.copy2(_ROUTING_TABLE, dest)
    print(f"Snapshot saved: {dest}")
    return 0


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def cmd_export(args: argparse.Namespace) -> int:
    """Bundle routing tables, playbooks, antipatterns, user_context (no task logs)."""
    out_path = Path(args.path)
    if out_path.is_dir():
        out_path = out_path / "learning_bundle.tar.gz"
    if not out_path.suffix:
        out_path = out_path.with_suffix(".tar.gz")

    # Ensure output dir exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    included: list[tuple[Path, str]] = []  # (src_path, arcname)

    def _add(src: Path, arcname: str) -> None:
        if src.exists():
            included.append((src, arcname))

    def _add_tree(src_dir: Path, arc_prefix: str) -> None:
        if not src_dir.is_dir():
            return
        for f in src_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(src_dir)
                included.append((f, f"{arc_prefix}/{rel}"))

    _add(_ROUTING_TABLE, "routing_table.json")
    _add(_USER_CONTEXT, "user_context.json")
    _add_tree(_ROUTING_HISTORY, "routing_history")
    _add_tree(_PLAYBOOKS_DIR, "playbooks")
    _add_tree(_ANTIPATTERNS_DIR, "antipatterns")

    if not included:
        print("WARNING: nothing to export (no learning data found)")
        return 0

    with tarfile.open(out_path, "w:gz") as tar:
        for src, arc in included:
            tar.add(str(src), arcname=arc)

    size_kb = out_path.stat().st_size // 1024
    print(f"Exported {len(included)} files → {out_path} ({size_kb} KB)")
    return 0


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

def _merge_routing(bundle_routing: Path) -> None:
    """Merge imported routing_table.json — keep highest-confidence per task type."""
    try:
        imported = json.loads(bundle_routing.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  SKIP routing_table.json (parse error: {e})")
        return

    if _ROUTING_TABLE.exists():
        try:
            current = json.loads(_ROUTING_TABLE.read_text(encoding="utf-8"))
        except Exception:
            current = {"task_types": {}}
    else:
        current = {"task_types": {}}

    current_types = current.setdefault("task_types", {})
    imported_types = imported.get("task_types", {})
    conflicts = 0

    for task_type, imp_entry in imported_types.items():
        if task_type not in current_types:
            current_types[task_type] = imp_entry
        else:
            cur_conf = float(current_types[task_type].get("confidence", 0.0))
            imp_conf = float(imp_entry.get("confidence", 0.0))
            if imp_conf > cur_conf:
                _log_conflict(
                    f"routing/{task_type}: replaced confidence {cur_conf:.2f} → {imp_conf:.2f}"
                )
                current_types[task_type] = imp_entry
                conflicts += 1
            else:
                _log_conflict(
                    f"routing/{task_type}: kept existing (conf {cur_conf:.2f} >= {imp_conf:.2f})"
                )

    current["last_updated"] = _now_iso()
    tmp = str(_ROUTING_TABLE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    os.replace(tmp, str(_ROUTING_TABLE))
    print(f"  routing_table.json merged ({conflicts} conflicts resolved — see import_conflicts.log)")


def _merge_antipatterns(bundle_ap_dir: Path) -> None:
    """Append antipattern entries not already present."""
    _ANTIPATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    merged = 0
    for src_file in bundle_ap_dir.glob("*.md"):
        dest = _ANTIPATTERNS_DIR / src_file.name
        new_text = src_file.read_text(encoding="utf-8")
        if dest.exists():
            existing = dest.read_text(encoding="utf-8")
            # Append only lines/blocks not already present (80-char key dedup)
            new_entries: list[str] = []
            for block in new_text.split("\n---\n"):
                key = block.strip()[:80]
                if key and key not in existing:
                    new_entries.append(block)
            if new_entries:
                with dest.open("a", encoding="utf-8") as f:
                    f.write("\n---\n" + "\n---\n".join(new_entries))
                merged += len(new_entries)
        else:
            dest.write_text(new_text, encoding="utf-8")
            merged += 1
    print(f"  antipatterns/: {merged} entries merged")


def _merge_playbooks(bundle_pb_dir: Path) -> None:
    """Copy playbook versions not present locally; keep higher success_rate if conflict."""
    _PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    for src_subdir in bundle_pb_dir.iterdir():
        if not src_subdir.is_dir():
            continue
        name = src_subdir.name
        dest_subdir = _PLAYBOOKS_DIR / name
        if not dest_subdir.exists():
            shutil.copytree(str(src_subdir), str(dest_subdir))
            copied += 1
        else:
            # Compare success_rate from meta.json
            src_meta = src_subdir / "meta.json"
            dst_meta = dest_subdir / "meta.json"
            try:
                src_rate = json.loads(src_meta.read_text(encoding="utf-8")).get("success_rate", 0.0)
                dst_rate = json.loads(dst_meta.read_text(encoding="utf-8")).get("success_rate", 0.0)
                if src_rate > dst_rate:
                    shutil.copytree(str(src_subdir), str(dest_subdir), dirs_exist_ok=True)
                    _log_conflict(f"playbook/{name}: replaced rate {dst_rate:.2f} → {src_rate:.2f}")
                    copied += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
    print(f"  playbooks/: {copied} updated, {skipped} kept existing")


def cmd_import(args: argparse.Namespace) -> int:
    """Merge a learning bundle into the current store."""
    bundle = Path(args.bundle)
    if not bundle.exists():
        print(f"ERROR: bundle not found: {bundle}")
        return 1

    # Extract to temp dir
    tmp_dir = _HERE / f"_import_tmp_{int(time.time())}"
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(bundle, "r:gz") as tar:
            tar.extractall(str(tmp_dir))
        print(f"Extracted bundle → {tmp_dir}")

        # Show diff summary before committing
        print("\nMerging:")

        routing_src = tmp_dir / "routing_table.json"
        if routing_src.exists():
            _merge_routing(routing_src)

        ap_src = tmp_dir / "antipatterns"
        if ap_src.is_dir():
            _merge_antipatterns(ap_src)

        pb_src = tmp_dir / "playbooks"
        if pb_src.is_dir():
            _merge_playbooks(pb_src)

        uc_src = tmp_dir / "user_context.json"
        if uc_src.exists():
            if _USER_CONTEXT.exists():
                print("  user_context.json: skipped (local takes precedence — edit manually)")
            else:
                shutil.copy2(uc_src, _USER_CONTEXT)
                print("  user_context.json: imported")

        print(f"\nImport complete. Conflicts logged to: {_CONFLICTS_LOG}")
        return 0
    except Exception as e:
        print(f"ERROR during import: {e}")
        return 1
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------

def _rollback_playbook(name: str) -> int:
    pb_dir = _PLAYBOOKS_DIR / name
    if not pb_dir.exists():
        print(f"ERROR: playbook '{name}' not found at {pb_dir}")
        return 1

    # Find all versioned files v1.md, v2.md, ...
    versions = sorted(pb_dir.glob("v*.md"), key=lambda p: int(p.stem[1:]) if p.stem[1:].isdigit() else 0)
    current_link = pb_dir / "current.md"

    if len(versions) < 2:
        print(f"ERROR: only {len(versions)} version(s) found — cannot roll back")
        return 1

    prev = versions[-2]
    shutil.copy2(prev, current_link)
    print(f"Rolled back playbook '{name}': current.md → {prev.name}")
    return 0


def _rollback_routing(days: int) -> int:
    if not _ROUTING_HISTORY.is_dir():
        print("ERROR: no routing_history/ found — run `snapshot` first")
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    snapshots = sorted(_ROUTING_HISTORY.glob("*.json"))
    if not snapshots:
        print("ERROR: no snapshots in routing_history/")
        return 1

    # Find latest snapshot at or before cutoff
    target: Path | None = None
    for snap in reversed(snapshots):
        try:
            stamp_str = snap.stem  # "YYYY-MM-DD-HH"
            snap_dt = datetime.strptime(stamp_str, "%Y-%m-%d-%H").replace(tzinfo=timezone.utc)
            if snap_dt <= cutoff:
                target = snap
                break
        except ValueError:
            continue

    if target is None:
        # Fall back to oldest
        target = snapshots[0]
        print(f"WARNING: no snapshot older than {days}d, using oldest: {target.name}")

    # Backup current before overwriting
    if _ROUTING_TABLE.exists():
        cmd_snapshot(argparse.Namespace())

    shutil.copy2(target, _ROUTING_TABLE)
    print(f"Routing table restored from snapshot: {target.name}")
    return 0


def _rollback_skill(skill_path: str) -> int:
    """Restore a skill file from its most recent backup."""
    safe = skill_path.replace("/", "_").replace("\\", "_").replace(".md", "")
    backup_dir = _SKILL_BACKUPS / safe
    if not backup_dir.is_dir():
        print(f"ERROR: no backups found for skill '{skill_path}' at {backup_dir}")
        return 1

    versions = sorted(backup_dir.glob("v*.md"), key=lambda p: int(p.stem[1:]) if p.stem[1:].isdigit() else 0)
    if not versions:
        print(f"ERROR: backup dir exists but no v*.md files found in {backup_dir}")
        return 1

    # Resolve target path relative to repo root
    repo_root = _HERE.parent.parent
    target = repo_root / skill_path
    if not target.parent.exists():
        print(f"ERROR: target directory does not exist: {target.parent}")
        return 1

    prev = versions[-1]
    shutil.copy2(prev, target)
    print(f"Skill '{skill_path}' restored from {prev}")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    sub = args.sub
    if sub == "playbook":
        if not args.name:
            print("ERROR: rollback playbook requires <name>")
            return 1
        return _rollback_playbook(args.name)
    elif sub == "routing":
        return _rollback_routing(args.days)
    elif sub == "skill":
        if not args.skill_path:
            print("ERROR: rollback skill requires <skill_path>")
            return 1
        return _rollback_skill(args.skill_path)
    else:
        print(f"ERROR: unknown rollback subcommand '{sub}'")
        return 1


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(_args: argparse.Namespace) -> int:
    """Print learning system status."""
    try:
        from helm.learning import is_learning_enabled
        enabled = is_learning_enabled()
    except Exception:
        enabled = False

    print(f"Learning: {'ENABLED' if enabled else 'DISABLED'}")

    if _ROUTING_TABLE.exists():
        try:
            rt = json.loads(_ROUTING_TABLE.read_text(encoding="utf-8"))
            types = rt.get("task_types", {})
            print(f"Routing table: {len(types)} task types tracked")
            for tt, entry in sorted(types.items()):
                best = entry.get("best_ai", "?")
                conf = entry.get("confidence", 0.0)
                n = entry.get("sample_count", 0)
                print(f"  {tt:25s}  best={best:10s}  conf={conf:.2f}  n={n}")
        except Exception as e:
            print(f"Routing table: ERROR ({e})")
    else:
        print("Routing table: not found")

    # Playbooks
    pb_count = sum(1 for d in _PLAYBOOKS_DIR.rglob("meta.json")
                   if _load_meta_status(d) == "active") if _PLAYBOOKS_DIR.exists() else 0
    print(f"Active playbooks: {pb_count}")

    # Snapshots
    snap_count = len(list(_ROUTING_HISTORY.glob("*.json"))) if _ROUTING_HISTORY.exists() else 0
    print(f"Routing snapshots: {snap_count}")

    try:
        from helm.learning.db import get_stats
        s = get_stats()
        print(f"Similarity index: {s['total_fingerprints']} fingerprints, {s['merged']} merged")
    except Exception:
        pass

    return 0


def _load_meta_status(meta_path: Path) -> str:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8")).get("status", "")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="helm learning",
        description="Helm HQ learning data management CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # export
    ep = sub.add_parser("export", help="Export learning bundle to .tar.gz")
    ep.add_argument("path", help="Output path (file or directory)")

    # import
    ip = sub.add_parser("import", help="Merge a learning bundle")
    ip.add_argument("bundle", help="Path to learning_bundle.tar.gz")

    # snapshot
    sub.add_parser("snapshot", help="Snapshot current routing table")

    # status
    sub.add_parser("status", help="Show learning system status")

    # rollback
    rp = sub.add_parser("rollback", help="Roll back a learning artifact")
    rsub = rp.add_subparsers(dest="sub", required=True)

    rpb = rsub.add_parser("playbook", help="Roll back playbook to previous version")
    rpb.add_argument("name", help="Playbook name")

    rrt = rsub.add_parser("routing", help="Restore routing table from snapshot")
    rrt.add_argument("--days", type=int, default=1, help="Days ago to restore (default: 1)")

    rsk = rsub.add_parser("skill", help="Restore skill file from backup")
    rsk.add_argument("skill_path", help="Relative path to skill file (e.g. .skills/skills/code/debug.md)")

    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_COMMANDS = {
    "export": cmd_export,
    "import": cmd_import,
    "snapshot": cmd_snapshot,
    "rollback": cmd_rollback,
    "status": cmd_status,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
