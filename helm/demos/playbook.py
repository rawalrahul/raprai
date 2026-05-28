from pathlib import Path
from helm.paths import HELM_DIR

PLAYBOOKS_DIR = HELM_DIR / "learning" / "playbooks"

_ACTION_ICONS = {
    "click": "🖱",
    "type": "⌨",
    "scroll": "↕",
    "keyboard_shortcut": "⌨",
    "navigate": "→",
    "wait": "⏳",
}


def actions_to_markdown(title: str, actions: list) -> str:
    lines = [f"# {title}", "", "## Steps", ""]
    for a in actions:
        step = a.get("step", "?")
        ts = a.get("timestamp", "")
        action = a.get("action", "")
        target = a.get("target", "")
        content = a.get("content", "")
        intent = a.get("intent", "")
        icon = _ACTION_ICONS.get(action, "•")
        line = f"{step}. `{ts}` {icon} **{action}** — {target}"
        if content:
            line += f" — `{content}`"
        lines.append(line)
        lines.append(f"   > {intent}")
    return "\n".join(lines) + "\n"


def save_playbook(title: str, actions: list) -> Path:
    out_dir = PLAYBOOKS_DIR / title
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "v1.md"
    path.write_text(actions_to_markdown(title, actions), encoding="utf-8")
    return path
