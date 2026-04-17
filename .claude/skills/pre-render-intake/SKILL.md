---
name: pre-render-intake
description: |
  MANDATORY before any paid video render (Seedance, Kling, Veo, Runway). A silent
  10-second clip of random cartoon motion is not a deliverable — it's wasted
  credit. Before composing a video prompt, interview the user on the seven
  dimensions that make a video actually usable: audio, dialogue, lipsync,
  on-screen text, style/realism, aspect/duration, and the story beat. If any
  answer is missing, ASK — don't guess. Invoke this skill the moment the user
  says "generate video" / "сгенерируй видео" and all hero/background assets
  are in place, right AFTER real-photo-avatar (if applicable) and BEFORE the
  fal/Kling curl.
triggers:
  - user says "generate video" / "сгенерируй видео" / "го"
  - user has sent hero(es) + background and is about to approve a render
  - a prior render came back and the user said it's "empty" / "useless" / "не то"
---

# Pre-render intake (7 questions the agent MUST ask)

## Why this exists

We already shipped a silent, contextless 10-second cartoon and the user called
it "an empty non-usable thing." He was right. A usable short video has at
minimum: audio, a reason to watch, and a recognizable style. The video model
won't invent those — we have to extract them from the user before paying for
pixels.

## The anti-pattern we are killing

> User sends 2 photos + "make a video" → agent composes a Pixar prompt →
> $0.45 Seedance call → silent MP4 of generic cartoon motion → user:
> "это пусто, так не пойдёт"

## The interview (ask in ONE message, not seven)

Send a single compact message with all seven questions. Offer sensible
defaults so the user can answer with "дефолты ок" and you proceed.

### Template (RU, adjust to user's language)

> Ок, герои и фон есть. Перед рендером уточни 7 вещей (или скажи «дефолты»):
>
> **1. Длительность / формат** — 10s 9:16 вертикаль для TG/TikTok (дефолт), или 5s / 15s / горизонт?
> **2. Стиль камеры** — realistic cinematic (дефолт), handheld, static, dynamic chase, dolly-zoom?
> **3. Звук/музыка** — без звука (дефолт, Seedance не умеет), бэкграунд-трек (добавлю через ffmpeg после), SFX?
> **4. Реплики героев** — молчат (дефолт), говорят (какую фразу?), лип-синк по твоему голосу?
> **5. Голосовой сэмпл** — если лип-синк: пришли 10-30с чистой речи, или TTS-голос из библиотеки?
> **6. Текст на экране** — нет (дефолт), hook-заголовок (какой?), CTA в конце (какой?), субтитры?
> **7. Story beat** — что происходит в сюжете? Начало → середина → конец. Без этого получится красивое пусто.
>
> Дефолты ок? Или уточнения по пунктам 3, 4, 7?

## Why each question matters

| # | Question | Why without it the video flops |
|---|----------|--------------------------------|
| 1 | Duration + aspect | Wrong ratio = unusable on target platform |
| 2 | Camera style | Default "orbit + crane shot" looks like every other AI demo |
| 3 | Audio | Silent video dies in feed. Needs music or SFX layer (added post via ffmpeg) |
| 4 | Dialogue | Heroes with moving mouths but no voice = uncanny |
| 5 | Voice sample | Enables lipsync via fal-ai/latentsync or sync.so |
| 6 | On-screen text | Hook in first 1s drives completion rate on TG/TikTok |
| 7 | Story beat | Prompt quality is capped by story clarity — no beat = generic motion |

## Post-processing pipeline (after video returns)

If the answers include audio/text/lipsync, the pipeline is:

```
raw Seedance mp4
  → lipsync (fal-ai/latentsync) if dialogue + voice sample
  → ffmpeg overlay for on-screen text (drawtext or ASS subtitles)
  → ffmpeg -i video -i audio -c:v copy -shortest for music/SFX bed
  → final.mp4
```

Relevant fal endpoints (verify before use):
- `fal.run/fal-ai/latentsync` — lipsync, takes video + audio, ≈$0.50/10s
- `fal.run/fal-ai/minimax/speech-02-turbo` — fast TTS with voice cloning, ≈$0.03/line
- `fal.run/fal-ai/stable-audio` — music/SFX generation, ≈$0.05/10s

## Dry-run announcement before spending

After the interview, show a consolidated plan with total cost:

> План:
> - Seedance image-to-video 10s ≈$0.45
> - TTS фразы "…" via minimax ≈$0.03
> - Lipsync latentsync ≈$0.50
> - Background music stable-audio ≈$0.05
> - ffmpeg сборка (бесплатно)
> **Итого ≈$1.03, ~4 минуты. "го" — запускаю.**

Only after "го" / explicit approval → spend credit.

## When to skip the interview

- User explicitly said "just render, no questions" / "быстро, без вопросов"
- This is iteration 2+ and the answers from iteration 1 still apply —
  ask only what changed
- Cron-driven autonomous run via `director.py --mode=...` — the calendar
  slot supplies all seven answers (see below)

## Autonomous mode — bake the 7 answers into the calendar

For 24/7 cron content, there is no human at 3am. Each `CALENDAR[hour]` slot
in `director.py` must carry a full answer set. Upgrade the calendar from
`{hour: (skill_dir, catchy_name)}` to:

```python
CALENDAR = {
  14: {
    "skill":    "skills/02-3d-cgi",
    "name":     "Pixar hour",
    "duration": 10,           # Q1
    "aspect":   "9:16",       # Q1
    "camera":   "cinematic",  # Q2
    "audio":    {"mode": "music", "prompt": "upbeat orchestral, 90 BPM"},  # Q3
    "dialogue": None,         # Q4 (or {"text": "...", "voice_id": "..."})
    "voice_sample": None,     # Q5
    "text":     {"hook": "Wait for it…", "cta": "Follow for more"},  # Q6
    "beat":     "setup → escalation → punchline",  # Q7
  },
  ...
}
```

The `assembler` agent then runs the post-processing pipeline (lipsync / TTS /
music / ffmpeg) automatically. If a slot is missing a dimension, default to
the safest silent-video + bottom-third hook overlay rather than shipping
raw Seedance output.

This mirrors how automated UGC farms (e.g. the Sirio-Berati-style Seedance
pipeline) operate: every post has a pre-declared hook, CTA, music track,
and voice line — the model never gets asked "what should happen here?" at
runtime.

## Failure log

- 2026-04-17 15:xx — shipped silent, textless, storyless 10s cartoon clip;
  user: "What we did yet is an empty non-usable thing." Root cause: skipped
  this intake entirely.
