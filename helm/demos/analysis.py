import asyncio
import json
import os
import re
from pathlib import Path

from helm.config import logger
from helm.demos import storage
from helm.demos.playbook import save_playbook

try:
    import static_ffmpeg as _static_ffmpeg
    _static_ffmpeg.add_paths()
except Exception:
    pass

_PROMPT = """Watch this screen recording carefully. List every action the user takes as a numbered step.

For each step include:
- timestamp (approximate)
- action type: click / type / scroll / keyboard_shortcut / navigate / wait
- target: what was clicked or where (button label, field name, URL, app name)
- content: text typed or key pressed (if applicable)
- intent: what this action accomplishes

Be exhaustive. Include every mouse click, every keystroke sequence, every navigation.
Output JSON array only. No prose."""


def extract_json_array(text: str) -> list:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in response")
    return json.loads(text[start:end + 1])


async def analyze_demo(demo_id: str, title: str) -> None:
    storage.update_meta(demo_id, {"status": "analyzing"})
    try:
        actions = await _run_analysis(demo_id)
        storage.save_actions(demo_id, actions)
        playbook_path = save_playbook(title, actions)
        storage.update_meta(demo_id, {
            "status": "ready",
            "playbook_path": str(playbook_path),
        })
    except Exception as exc:
        logger.error("demo analysis failed demo_id=%s: %s", demo_id, exc)
        storage.update_meta(demo_id, {"status": "error", "error_message": str(exc)})


async def _run_analysis(demo_id: str) -> list:
    video_path = storage.get_video_path(demo_id)
    if video_path is None:
        raise FileNotFoundError(f"No video file for demo {demo_id}")

    errors: list[str] = []

    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        try:
            return await asyncio.to_thread(_analyze_gemini, demo_id, video_path)
        except Exception as e:
            logger.warning("Gemini analysis failed: %s", e)
            errors.append(f"Gemini: {e}")

    frames: list[Path] = []

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            frames = await asyncio.to_thread(
                _extract_frames, video_path, storage.get_frames_dir(demo_id)
            )
            return await asyncio.to_thread(_analyze_claude, frames)
        except Exception as e:
            logger.warning("Claude analysis failed: %s", e)
            errors.append(f"Claude: {e}")

    if os.environ.get("OPENAI_API_KEY"):
        try:
            if not frames:
                frames = await asyncio.to_thread(
                    _extract_frames, video_path, storage.get_frames_dir(demo_id)
                )
            return await asyncio.to_thread(_analyze_openai, frames)
        except Exception as e:
            logger.warning("OpenAI analysis failed: %s", e)
            errors.append(f"OpenAI: {e}")

    raise RuntimeError(
        f"All analysis paths failed: {'; '.join(errors) or 'no API keys configured'}"
    )


def _analyze_gemini(demo_id: str, video_path: Path) -> list:
    import mimetypes
    import time
    from datetime import datetime, timedelta, timezone

    import google.genai as genai

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=key)

    meta = storage._read_meta(demo_id) or {}
    file_obj = None

    gemini_file_name = meta.get("gemini_file_name")
    expires_at_str = meta.get("file_uri_expires_at")
    if gemini_file_name and expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(timezone.utc) < expires_at:
            try:
                cached = client.files.get(name=gemini_file_name)
                file_obj = cached if cached.state.name == "ACTIVE" else None
            except Exception:
                file_obj = None

    if file_obj is None:
        mime = mimetypes.guess_type(str(video_path))[0] or "video/mp4"
        uploaded = client.files.upload(
            path=str(video_path), config={"mime_type": mime}
        )
        for _ in range(60):
            f = client.files.get(name=uploaded.name)
            if f.state.name == "ACTIVE":
                break
            time.sleep(1)
        else:
            raise TimeoutError("Gemini file did not become ACTIVE within 60 seconds")
        file_obj = f
        expires_at = datetime.now(timezone.utc) + timedelta(hours=47)
        storage.update_meta(demo_id, {
            "analysis_ai": "gemini",
            "file_uri": uploaded.uri,
            "gemini_file_name": uploaded.name,
            "file_uri_expires_at": expires_at.isoformat(),
        })

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[file_obj, _PROMPT],
    )
    return extract_json_array(response.text)


def _extract_frames(video_path: Path, frames_dir: Path) -> list[Path]:
    import subprocess
    frames_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", r"fps=1,select=gt(scene\,0.3)",
        "-vsync", "vfr",
        str(frames_dir / "frame_%04d.jpg"),
        "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
    frames = sorted(frames_dir.glob("*.jpg"))[:30]
    if not frames:
        raise RuntimeError("ffmpeg produced no keyframes")
    return frames


def _analyze_claude(frames: list[Path]) -> list:
    import base64
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    content: list[dict] = []
    for frame in frames[:30]:
        data = base64.standard_b64encode(frame.read_bytes()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
        })
    content.append({"type": "text", "text": _PROMPT})
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    return extract_json_array(response.content[0].text)


def _analyze_openai(frames: list[Path]) -> list:
    import base64
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    content: list[dict] = [{"type": "text", "text": _PROMPT}]
    for frame in frames[:30]:
        data = base64.standard_b64encode(frame.read_bytes()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{data}"},
        })
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=4096,
    )
    return extract_json_array(response.choices[0].message.content)
