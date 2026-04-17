#!/usr/bin/env python3
"""
vaibe-auto: multi-agent AI film director.

Name: V(ideo) + A(I) + I(mproved/Intelligent) + B(etter) + E(dits) + auto.
Sounds like "vibe," spelled with the letters that mean something.

LLM modes:
  --mode=claude      Anthropic API (paid, highest quality)
  --mode=zero        Local OpenAI-compatible endpoint (LM Studio / Ollama, free)
  --mode=openrouter  OpenRouter (many :free models + paid if needed)

Pipeline: story -> script_breakdown -> shot_designer -> prompt_writer -> fal_runner -> assembler

Usage:
    export ANTHROPIC_API_KEY=sk-...
    export FAL_KEY=fal-...
    python director.py --mode=claude     --story "A samurai meets an AI in Tokyo rain."
    python director.py --mode=zero       --story "A cat discovers ikigai at dawn."
    python director.py --mode=openrouter --story "A lone fox crosses a neon alley."
    python director.py --hour 03                            # use 24h calendar slot

Requires: requests, (optional) anthropic, ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # we fall back to urllib where possible

ROOT = pathlib.Path(__file__).resolve().parent
SKILLS_DIR = ROOT.parent / "skills"
OUTPUT_DIR = ROOT / "output"
LOGS_DIR = ROOT / "logs"
ASSETS_DIR = ROOT / "assets"
HERO_DIR = ASSETS_DIR / "hero"
BG_DIR = ASSETS_DIR / "background"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
HERO_DIR.mkdir(parents=True, exist_ok=True)
BG_DIR.mkdir(parents=True, exist_ok=True)


def _pick_image(folder: pathlib.Path) -> pathlib.Path | None:
    if not folder.is_dir():
        return None
    images = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    return images[0] if images else None


def pick_hero(hour: int | None) -> pathlib.Path | None:
    """Pick a hero image: assets/hero/heroN/ rotated by hour (N = #subfolders)."""
    subs = sorted(p for p in HERO_DIR.iterdir() if p.is_dir()) if HERO_DIR.is_dir() else []
    if not subs:
        return _pick_image(HERO_DIR)
    idx = (hour if hour is not None else 0) % len(subs)
    return _pick_image(subs[idx])


def pick_background() -> pathlib.Path | None:
    return _pick_image(BG_DIR)

# ---------------------------------------------------------------------------
# 24-hour catchy content calendar (hour -> (skill_dir, catchy_name))
# ---------------------------------------------------------------------------
CALENDAR: dict[int, tuple[str, str]] = {
    0:  ("21-asmr-ambient",           "Midnight Silk"),
    1:  ("19-horror-thriller",        "3AM Dread"),
    2:  ("16-short-drama",            "Sleepless Confessions"),
    3:  ("18-character-consistency",  "Ghost Protocol"),
    4:  ("20-travel-landscape",       "Blue Hour Drift"),
    5:  ("22-news-documentary",       "Dawn Dispatch"),
    6:  ("17-educational",            "First Light Lesson"),
    7:  ("14-food-beverage",          "Morning Ritual"),
    8:  ("12-brand-story",            "Origin Story"),
    9:  ("06-motion-design-ad",       "9 to Thrive"),
    10: ("01-cinematic",              "Golden Window"),
    11: ("11-social-hook",            "Scroll Breaker"),
    12: ("07-ecommerce-ad",           "Lunch Impulse"),
    13: ("09-product-360",            "The Reveal"),
    14: ("02-3d-cgi",                 "Rendered Reality"),
    15: ("10-music-video",            "Afternoon Beat"),
    16: ("08-anime-action",           "Rush Hour Clash"),
    17: ("13-fashion-lookbook",       "Golden Hour Fit"),
    18: ("23-sports-action",          "End of Day Grind"),
    19: ("15-real-estate",            "Dream Door"),
    20: ("04-comic-to-video",         "Panel Explosion"),
    21: ("03-cartoon",                "Bedtime Chaos"),
    22: ("05-fight-scenes",           "Last Round"),
    23: ("24-fal-runner",             "Night Render"),
}

# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------
MODES = {"claude", "zero", "openrouter"}


class LLM:
    """Unified interface for three LLM backends:
      - claude:      Anthropic API (paid)
      - zero:        local OpenAI-compatible endpoint (LM Studio / Ollama)
      - openrouter:  OpenRouter (hosted, many :free models)
    """

    def __init__(self, mode: str, log_path: pathlib.Path):
        self.mode = mode
        self.log_path = log_path
        self.extra_headers: dict[str, str] = {}
        if mode == "claude":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                sys.exit("ANTHROPIC_API_KEY not set — need it for --mode=claude")
            self.model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
        elif mode == "zero":
            self.endpoint = os.environ.get("LMSTUDIO_URL", "http://localhost:1234/v1/chat/completions")
            self.model = os.environ.get("LMSTUDIO_MODEL", "miniqwen")
            self.api_key = os.environ.get("LMSTUDIO_API_KEY", "")  # LM Studio ignores it
        elif mode == "openrouter":
            self.endpoint = os.environ.get("OPENROUTER_URL",
                                           "https://openrouter.ai/api/v1/chat/completions")
            self.model = os.environ.get("OPENROUTER_MODEL",
                                        "deepseek/deepseek-chat-v3:free")
            self.api_key = os.environ.get("OPENROUTER_API_KEY")
            if not self.api_key:
                sys.exit("OPENROUTER_API_KEY not set — need it for --mode=openrouter")
            # Optional OpenRouter attribution headers
            self.extra_headers = {
                "HTTP-Referer": os.environ.get("OPENROUTER_REFERER", "https://github.com/tixuz/vaibe-auto"),
                "X-Title": os.environ.get("OPENROUTER_TITLE", "vaibe-auto"),
            }
        else:
            sys.exit(f"unknown mode: {mode} (expected one of {sorted(MODES)})")

    def _log(self, agent: str, prompt: str, reply: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"\n===== {agent} ({self.mode}/{self.model}) =====\n")
            f.write(f"--- prompt ---\n{prompt}\n--- reply ---\n{reply}\n")

    def chat(self, agent: str, system: str, user: str, max_tokens: int = 1500) -> str:
        if self.mode == "claude":
            reply = self._claude(system, user, max_tokens)
        else:
            reply = self._openai_compat(system, user, max_tokens)
        self._log(agent, f"[SYSTEM]\n{system}\n[USER]\n{user}", reply)
        return reply

    def _claude(self, system: str, user: str, max_tokens: int) -> str:
        body = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["content"][0]["text"]

    def _openai_compat(self, system: str, user: str, max_tokens: int) -> str:
        """OpenAI-compatible chat completions — works for LM Studio, Ollama, OpenRouter."""
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:500]
            sys.exit(f"{self.mode} HTTP {e.code} at {self.endpoint}: {body}")
        except urllib.error.URLError as e:
            hint = ("Start LM Studio (load any OpenAI-compat model)."
                    if self.mode == "zero" else
                    "Check OpenRouter status / network.")
            sys.exit(f"{self.mode} unreachable at {self.endpoint}: {e}\n{hint}")
        if "choices" not in data:
            sys.exit(f"{self.mode} unexpected reply: {json.dumps(data)[:400]}")
        return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict | list:
    """Pull the first JSON object/array out of an LLM reply."""
    m = re.search(r"```json\s*(.+?)```", text, re.S) or re.search(r"```\s*(.+?)```", text, re.S)
    if m:
        text = m.group(1)
    # first {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        i = text.find(opener)
        if i == -1:
            continue
        depth = 0
        for j in range(i, len(text)):
            if text[j] == opener:
                depth += 1
            elif text[j] == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(text[i : j + 1])
    raise ValueError(f"no JSON found in reply:\n{text[:500]}")


# ---------------------------------------------------------------------------
# Skill loader
# ---------------------------------------------------------------------------
def load_skill(skill_dir: str) -> str:
    path = SKILLS_DIR / skill_dir / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"missing skill: {path}")
    return path.read_text(encoding="utf-8")


def list_skills() -> list[str]:
    return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
def agent_script_breakdown(llm: LLM, story: str) -> list[dict]:
    """Break a story into 3-5 shots."""
    system = (
        "You are a film script breakdown agent. Given a one-line story, split it into "
        "3 to 5 vivid cinematic shots. Return ONLY JSON array of objects with keys: "
        "id (int, 1-based), beat (string: what happens), mood (string), duration_sec (int, 5-10)."
    )
    reply = llm.chat("script_breakdown", system, f"Story: {story}\n\nReturn JSON only.", 1200)
    shots = extract_json(reply)
    if not isinstance(shots, list):
        raise ValueError("script_breakdown must return a JSON array")
    return shots


def agent_shot_designer(llm: LLM, shot: dict, preferred: str | None = None) -> str:
    """Pick the best skill for this shot. If preferred is set, just use it."""
    if preferred:
        return preferred
    skills = list_skills()
    system = (
        "You are a shot designer. Pick ONE skill name from the list that best fits the shot. "
        'Return ONLY JSON: {"skill": "<exact-skill-dir-name>"}'
    )
    user = f"Shot: {json.dumps(shot)}\n\nSkills:\n" + "\n".join(skills)
    reply = llm.chat("shot_designer", system, user, 200)
    choice = extract_json(reply)
    skill = choice["skill"]
    if skill not in skills:
        # Fuzzy fallback
        for s in skills:
            if skill.lower() in s.lower():
                return s
        return "01-cinematic"
    return skill


def agent_prompt_writer(llm: LLM, shot: dict, skill_dir: str) -> dict:
    """Apply the selected skill to produce a fal.ai-ready prompt + parameters."""
    skill_md = load_skill(skill_dir)
    # Keep skill content bounded for the local model
    skill_md_trimmed = skill_md[:3000]  # keep context lean; full skill rarely needed for prompting
    system = (
        "You are a Seedance 2.0 prompt writer. Using the provided SKILL.md guidelines, "
        "craft a single vivid prompt for the shot. Return ONLY JSON with keys: "
        'prompt (string, <= 900 chars), aspect_ratio ("16:9"|"9:16"|"1:1"), '
        "duration_sec (int 3-6), resolution (\"720p\"|\"1080p\")."
    )
    user = (
        f"SHOT: {json.dumps(shot)}\n\n"
        f"SKILL ({skill_dir}):\n{skill_md_trimmed}\n\n"
        "Return JSON only."
    )
    reply = llm.chat(f"prompt_writer[{skill_dir}]", system, user, 1200)
    data = extract_json(reply)
    data.setdefault("aspect_ratio", "16:9")
    data.setdefault("duration_sec", shot.get("duration_sec", 5))  # 5s default; use --duration to override
    data.setdefault("resolution", "720p")  # 720p default — ~40% cheaper, phones can't tell difference
    return data


def _data_uri(path: pathlib.Path) -> str:
    import base64, mimetypes
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


PROVIDERS = {
    "fal": {
        "text": "https://fal.run/bytedance/seedance-2.0/text-to-video",
        "image": "https://fal.run/bytedance/seedance-2.0/image-to-video",
        "auth": lambda k: {"Authorization": f"Key {k}"},
        "env": "FAL_KEY",
    },
    "fal-fast": {
        "text": "https://fal.run/bytedance/seedance-2.0/fast/text-to-video",
        "image": "https://fal.run/bytedance/seedance-2.0/fast/image-to-video",
        "auth": lambda k: {"Authorization": f"Key {k}"},
        "env": "FAL_KEY",
    },
    "fal-ltx": {
        # LTX Video on fal — ultra-cheap B-roll tier (~$0.08/clip).
        # ~10× cheaper than Seedance standard; lower fidelity but fine for
        # hourly cron fillers, loops, abstract/texture shots.
        "text":  "https://fal.run/fal-ai/ltx-video-13b-distilled/multiconditioning",
        "image": "https://fal.run/fal-ai/ltx-video-13b-distilled/multiconditioning",
        "auth":  lambda k: {"Authorization": f"Key {k}"},
        "env":   "FAL_KEY",
    },
    "enhancor": {
        # Enhancor.ai — cheaper Seedance 2 (-45% base, code SAVE25 stacks to -75%).
        # Endpoints per Enhancor API docs.
        "text": "https://api.enhancor.ai/v1/seedance/v2/text-to-video",
        "image": "https://api.enhancor.ai/v1/seedance/v2/image-to-video",
        "auth": lambda k: {"Authorization": f"Bearer {k}"},
        "env": "ENHANCOR_API_KEY",
    },
    "openrouter": {
        # OpenRouter unified video endpoint — async (submit → poll → download).
        # Single endpoint, per-model routing via the "model" field in the body.
        # Docs: https://openrouter.ai/docs/api/api-reference/video-generation/create-videos
        "url": "https://openrouter.ai/api/v1/videos",
        "auth": lambda k: {"Authorization": f"Bearer {k}"},
        "env": "OPENROUTER_API_KEY",
        "is_async": True,
        "default_model": "bytedance/seedance-2.0",
        "model_aliases": {
            # short alias -> canonical OpenRouter model id
            "seedance-2.0":     "bytedance/seedance-2.0",
            "seedance-2.0-pro": "bytedance/seedance-2.0-pro",
            "veo-3.1":          "google/veo-3.1",
            "veo-3.1-fast":     "google/veo-3.1-fast",
            "sora-2":           "openai/sora-2",
            "sora-2-pro":       "openai/sora-2-pro",
        },
    },
}


def agent_openrouter_runner(prompt_payload: dict, out_path: pathlib.Path,
                            log_path: pathlib.Path, *,
                            prov: dict, api_key: str,
                            hero: pathlib.Path | None = None,
                            background: pathlib.Path | None = None,
                            model: str | None = None,
                            confirm: bool = False) -> pathlib.Path:
    """Submit a job to OpenRouter /api/v1/videos, poll, then download.

    Async flow: POST returns {id, polling_url, status}. We poll the
    polling_url until status=completed, then fetch unsigned_urls[0].
    """
    # Resolve model id via aliases; default to provider default.
    raw_model = model or prov["default_model"]
    resolved_model = prov["model_aliases"].get(raw_model, raw_model)

    payload: dict = {
        "model": resolved_model,
        "prompt": prompt_payload["prompt"],
        "aspect_ratio": prompt_payload["aspect_ratio"],
        "duration": int(prompt_payload["duration_sec"]),
        "resolution": prompt_payload["resolution"],
    }
    if hero and hero.exists():
        # image-to-video: attach as input_references (per OpenRouter spec).
        payload["input_references"] = [{
            "type": "image_url",
            "image_url": {"url": _data_uri(hero)},
        }]
    if background and background.exists():
        payload["prompt"] += "\n\nBackground reference attached as style anchor."
        payload.setdefault("input_references", []).append({
            "type": "image_url",
            "image_url": {"url": _data_uri(background)},
        })

    url = prov["url"]
    headers = {"Content-Type": "application/json", **prov["auth"](api_key)}

    safe = {k: (v if k != "input_references"
                else f"<{len(v)} image_url refs>")
            for k, v in payload.items()}
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n===== openrouter_runner [{resolved_model}] -> {out_path.name} =====\n"
                f"{json.dumps(safe, indent=2)}\n")

    if confirm:
        print(f"\n── payload preview [openrouter / {resolved_model}] ─────────────")
        print(json.dumps(safe, indent=2, ensure_ascii=False)[:1500])
        print(f"── target: {url}")
        if input("proceed? [y/N] ").strip().lower() != "y":
            raise SystemExit("aborted by --confirm")

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        submit = json.loads(r.read().decode("utf-8"))

    polling_url = submit.get("polling_url")
    job_id = submit.get("id") or submit.get("generation_id")
    if not polling_url and job_id:
        polling_url = f"https://openrouter.ai/api/v1/videos/{job_id}"
    if not polling_url:
        raise RuntimeError(f"openrouter returned no polling_url: {submit}")

    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[openrouter] submitted id={job_id} polling={polling_url}\n")

    # Poll until terminal status. Typical jobs 30-180s; cap at 20 min.
    deadline = time.time() + 1200
    status = submit.get("status", "pending")
    result: dict = submit
    poll_headers = prov["auth"](api_key)
    while status in ("pending", "in_progress", "queued"):
        if time.time() > deadline:
            raise RuntimeError(f"openrouter job {job_id} timed out; last status={status}")
        time.sleep(5)
        preq = urllib.request.Request(polling_url, headers=poll_headers, method="GET")
        with urllib.request.urlopen(preq, timeout=60) as r:
            result = json.loads(r.read().decode("utf-8"))
        status = result.get("status", status)
        print(f"       [openrouter] status={status}")

    if status != "completed":
        raise RuntimeError(f"openrouter job {job_id} ended status={status}: "
                           f"{result.get('error')}")

    urls = result.get("unsigned_urls") or []
    if not urls:
        raise RuntimeError(f"openrouter completed but no unsigned_urls: {result}")
    video_url = urls[0]

    with urllib.request.urlopen(video_url, timeout=600) as r, out_path.open("wb") as f:
        f.write(r.read())

    cost = (result.get("usage") or {}).get("cost")
    if cost is not None:
        print(f"       [openrouter] cost ~${cost:.3f}")
    return out_path


def agent_fal_runner(prompt_payload: dict, out_path: pathlib.Path, log_path: pathlib.Path,
                     hero: pathlib.Path | None = None,
                     background: pathlib.Path | None = None,
                     provider: str = "fal",
                     model: str | None = None,
                     confirm: bool = False) -> pathlib.Path:
    """Call Seedance 2.0 via the chosen provider and download the resulting video.

    If `hero` is provided, calls image-to-video (hero = @Image1 reference).
    Background image is appended to the prompt as a style hint via data URI.
    """
    prov = PROVIDERS.get(provider)
    if not prov:
        raise RuntimeError(f"unknown provider: {provider}")
    api_key = os.environ.get(prov["env"])
    if not api_key:
        raise RuntimeError(f"{prov['env']} not set — needed for provider={provider}")
    if prov.get("is_async"):
        return agent_openrouter_runner(prompt_payload, out_path, log_path,
                                       prov=prov, api_key=api_key,
                                       hero=hero, background=background,
                                       model=model, confirm=confirm)
    if hero and hero.exists():
        url = prov["image"]
        endpoint_kind = "image-to-video"
        # Content-policy warning: Seedance rejects real photos of minors,
        # public figures, NSFW. If the filename hints at a real photo and
        # NOT a stylized asset, warn the user before burning credit.
        hero_str = str(hero).lower()
        stylized_markers = ("cartoon", "3d", "anime", "illust", "stylized",
                            "pixar", "disney", "nano", "flux", "kontext")
        looks_stylized = any(m in hero_str for m in stylized_markers)
        photo_markers = ("img_", "dsc", "photo", "selfie", "raw", "live")
        looks_photographic = any(m in hero_str for m in photo_markers)
        if looks_photographic and not looks_stylized:
            print("")
            print("  ⚠️  Hero filename looks like a raw photo "
                  "(IMG_/DSC/photo/selfie/...).")
            print("     Seedance 2.0 often REJECTS real photos of people "
                  "(especially minors & public figures).")
            print("     Safer route: stylize first →  "
                  "python3 stylize.py <photo> --style 3d")
            print("                  → reuse the avatar PNG in assets/hero/...")
            print("     Proceeding as requested — moderation may reject; "
                  "no refund for rejected jobs.")
            print("")
            if confirm:
                choice = input("  [s]tylize first / [p]roceed anyway / [a]bort ? ").strip().lower()
                if choice.startswith("s"):
                    sys.exit("Stop requested — run stylize.py first, then re-run director.py.")
                if choice.startswith("a") or choice == "":
                    sys.exit("Aborted by user at moderation warning.")
                # anything else → proceed
    payload = {
        "prompt": prompt_payload["prompt"],
        "aspect_ratio": prompt_payload["aspect_ratio"],
        "duration": str(prompt_payload["duration_sec"]),
        "resolution": prompt_payload["resolution"],
    }
    if provider == "enhancor":
        promo = os.environ.get("ENHANCOR_PROMO")
        if promo:
            payload["promo_code"] = promo
    if hero and hero.exists():
        payload["image_url"] = _data_uri(hero)
    if background and background.exists():
        payload["prompt"] += f"\n\nBackground reference attached as style anchor."
        payload["background_image_url"] = _data_uri(background)
    headers = {"Content-Type": "application/json", **prov["auth"](api_key)}
    body = json.dumps(payload).encode("utf-8")

    safe = {k: (v if not str(v).startswith("data:") else f"<{k}: {len(v)} bytes base64>")
            for k, v in payload.items()}
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n===== {provider}_runner [{endpoint_kind}] -> {out_path.name} =====\n"
                f"{json.dumps(safe, indent=2)}\n")

    if confirm:
        print(f"\n── payload preview [{provider}/{endpoint_kind}] ─────────────")
        print(json.dumps(safe, indent=2, ensure_ascii=False)[:1500])
        print(f"── target: {url}")
        if input("proceed? [y/N] ").strip().lower() != "y":
            raise SystemExit("aborted by --confirm")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.loads(r.read().decode("utf-8"))

    video_url = (data.get("video") or {}).get("url") or data.get("video_url")
    if not video_url:
        raise RuntimeError(f"fal.ai returned no video URL: {data}")
    with urllib.request.urlopen(video_url, timeout=600) as r, out_path.open("wb") as f:
        f.write(r.read())
    return out_path


def agent_assembler(clips: list[pathlib.Path], out_path: pathlib.Path) -> pathlib.Path:
    """Stitch clips with ffmpeg concat. Falls back to copying the single clip."""
    if len(clips) == 1:
        import shutil
        shutil.copy(clips[0], out_path)
        return out_path
    listfile = out_path.with_suffix(".txt")
    listfile.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
           "-c", "copy", str(out_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Fallback: re-encode
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
               "-c:v", "libx264", "-c:a", "aac", str(out_path)]
        subprocess.run(cmd, check=True)
    finally:
        listfile.unlink(missing_ok=True)
    return out_path


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run(mode: str, story: str, preferred_skill: str | None, slug: str, dry_run: bool,
        hour: int | None = None, provider: str = "fal",
        model: str | None = None,
        resolution: str | None = None,
        duration: int | None = None,
        confirm: bool = False) -> None:
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = LOGS_DIR / f"{ts}-{slug}.log"
    llm = LLM(mode, log_path)

    print(f"[director] mode={mode}  story={story!r}")
    print(f"[director] log -> {log_path}")

    print("[1/5] script breakdown…")
    shots = agent_script_breakdown(llm, story)
    print(f"       {len(shots)} shots")

    plans: list[tuple[dict, str, dict]] = []
    for shot in shots:
        print(f"[2/5] shot {shot['id']} — picking skill…")
        skill = agent_shot_designer(llm, shot, preferred_skill)
        print(f"       -> {skill}")
        print(f"[3/5] shot {shot['id']} — writing prompt…")
        payload = agent_prompt_writer(llm, shot, skill)
        # CLI overrides — cut cost/length without touching the skills.
        if resolution:
            payload["resolution"] = resolution
        if duration:
            payload["duration_sec"] = duration
        print(f"       prompt: {payload['prompt'][:80]}…")
        plans.append((shot, skill, payload))

    plan_path = OUTPUT_DIR / f"{ts}-{slug}.plan.json"
    plan_path.write_text(json.dumps(
        [{"shot": s, "skill": sk, "payload": p} for s, sk, p in plans],
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[plan] {plan_path}")

    hero = pick_hero(hour)
    bg = pick_background()
    if hero:
        print(f"[assets] hero -> {hero.relative_to(ROOT)}")
    if bg:
        print(f"[assets] background -> {bg.relative_to(ROOT)}")

    if dry_run:
        print("[dry-run] skipping fal.ai + assembly")
        return

    clips: list[pathlib.Path] = []
    for shot, skill, payload in plans:
        clip = OUTPUT_DIR / f"{ts}-{slug}-shot{shot['id']:02d}.mp4"
        # Auto-tier: if no hero asset exists, downgrade to the cheap B-roll provider
        # unless user explicitly chose a premium provider.
        shot_provider = provider
        if provider == "fal-fast" and not hero:
            shot_provider = "fal-ltx"
            print(f"[4/5] shot {shot['id']} — no hero → auto-downgrade to fal-ltx (~$0.08) -> {clip.name}")
        else:
            print(f"[4/5] shot {shot['id']} — {shot_provider} rendering -> {clip.name}")
        agent_fal_runner(payload, clip, log_path, hero=hero, background=bg,
                         provider=shot_provider, model=model, confirm=confirm)
        clips.append(clip)

    print("[5/5] assembling…")
    final = OUTPUT_DIR / f"{ts}-{slug}.final.mp4"
    agent_assembler(clips, final)
    print(f"[done] {final}")


def main() -> None:
    ap = argparse.ArgumentParser(description="vaibe-auto — multi-agent AI film director")
    ap.add_argument("--mode", choices=sorted(MODES), default="openrouter",
                    help="claude = Anthropic API (paid); zero = local LM Studio/Ollama (free); "
                         "openrouter = OpenRouter (many :free models, set OPENROUTER_API_KEY)")
    ap.add_argument("--story", help="One-line story prompt")
    ap.add_argument("--hour", type=int, help="0-23, use the 24-hour content calendar slot")
    ap.add_argument("--skill", help="Force a specific skill dir (bypass shot_designer)")
    ap.add_argument("--slug", default="clip", help="Output filename slug")
    ap.add_argument("--dry-run", action="store_true", help="Plan only, no video calls")
    ap.add_argument("--provider", choices=list(PROVIDERS.keys()), default="fal-fast",
                    help="fal = Seedance 2.0 standard (~$1.00/8s@1080p, premium); "
                         "fal-fast = Seedance 2.0 Fast (~$0.50/8s@1080p, DEFAULT, 90%% quality); "
                         "fal-ltx = LTX Video 13b distilled (~$0.08/5s, 10× cheaper — B-roll/filler tier); "
                         "enhancor = Enhancor.ai (paid subscription); "
                         "openrouter = OpenRouter unified video (Seedance/Veo/Sora via --model)")
    ap.add_argument("--model", default=None,
                    help="For --provider openrouter: model alias or full id "
                         "(seedance-2.0 | veo-3.1 | sora-2-pro | bytedance/seedance-2.0-pro | ...). "
                         "Ignored for fal/enhancor providers.")
    ap.add_argument("--resolution", choices=["480p", "720p", "1080p"], default="720p",
                    help="Override per-shot resolution. 720p (default) is ~40%% cheaper "
                         "than 1080p and looks identical on phones. 480p ~70%% cheaper.")
    ap.add_argument("--duration", type=int, default=None,
                    help="Override per-shot duration in seconds (e.g. 3, 5). "
                         "Default: whatever the prompt_writer chose (usually 6). "
                         "Shorter = cheaper. TikTok/Reels cut hard at 3s anyway.")
    ap.add_argument("--confirm", action="store_true",
                    help="Show payload and ask y/N before each paid API call")
    args = ap.parse_args()

    if args.hour is not None:
        skill_dir, name = CALENDAR[args.hour % 24]
        story = args.story or f"A {name} vibe — pure visual poem at {args.hour:02d}:00."
        args.skill = args.skill or skill_dir
        args.slug = f"h{args.hour:02d}-{name.lower().replace(' ', '-')}"
    else:
        story = args.story
        if not story:
            sys.exit("--story required (or use --hour)")

    run(args.mode, story, args.skill, args.slug, args.dry_run,
        hour=args.hour, provider=args.provider, model=args.model,
        resolution=args.resolution, duration=args.duration,
        confirm=args.confirm)


if __name__ == "__main__":
    main()
