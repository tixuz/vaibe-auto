# Notes for Claude Code sessions working in vaibe-auto

> **Before replying to ANY Telegram message in this repo, invoke these skills in order:**
>
> 1. `real-photo-avatar` (`.claude/skills/real-photo-avatar/SKILL.md`) — if the
>    message contains or references a real human photo. Failed in prod twice already.
> 2. `pre-render-intake` (`.claude/skills/pre-render-intake/SKILL.md`) — before
>    ANY paid video render, ask the 7 intake questions (audio, dialogue,
>    lipsync, text, style, duration, story beat). Skipping this gave the user
>    a silent useless clip and the feedback "an empty non-usable thing."

---

## 🚨 HARD RULE #1 — Real photos of people MUST be stylized BEFORE Seedance

**Do not rationalize your way past this.** A Pixar-quality prompt does NOT
bypass the moderator — the moderator only sees the raw image. "Let's try
Kling instead" does NOT work — same filters. The ONLY fix is to stylize
the image itself via `stylize.py` before any video call.

**Known failure log (do not repeat):**
- 2026-04-17 15:06 — photo of two daughters → Seedance image-to-video → rejected
- 2026-04-17 15:11 — same photo as `@Image1` in text-to-video prompt → rejected
- 2026-04-18 — AI-generated adult male avatar (flux-kontext stylized) → Seedance → ALSO rejected. Seedance moderates ALL realistic human faces, not just minors. Fallback was Kling — WRONG (same moderation, also expensive at $0.07/s).

**🚨 HARD RULE #2 — Seedance rejects realistic human faces period. Kling is NOT a fallback.**
- Seedance = no real photos, no realistic AI faces, no identifiable humans
- Kling = same moderation policy + more expensive → NEVER use as fallback for rejected Seedance jobs
- **Correct fallback for human-face video: `fal-wan` or `fal-wan26`** — Wan 2.5/2.6 has no such moderation on AI-generated faces and costs $0.05/s (cheapest in class)

**Trigger**: the user sends a photo via Telegram (or via file path) that contains
an identifiable real human face — especially their kids, family, or themselves.

**What you MUST do — in this exact order**:

1. **Stop.** Do NOT upload the raw photo to any Seedance endpoint
   (`fal.run/bytedance/seedance-2.0/...`). It will be moderated and rejected,
   wasting the user's credit AND their time.

2. **Announce your detour in one sentence** before doing anything:
   > "Это реальное фото человека — Seedance такое отклонит. Делаю сначала
   > стилизованную аватарку через flux-kontext (≈$0.04), потом её используем."

3. **Offer a choice of stylization model and style**, default to flux-kontext + 3d:
   ```
   Модели: flux-kontext (≈$0.04, дефолт) | nano-banana (≈$0.04, Google, сохраняет лицо)
           | seededit (≈$0.03, самая дешёвая) | qwen-edit (≈$0.03, аниме)
           | flux-kontext-max (≈$0.08, топ качество) | ideogram (≈$0.06, с текстом)
           | gpt-image (≈$0.07, OpenAI)
   Стили:  3d (Pixar) | anime (Ghibli) | comic | disney | claymation | <custom>
   ```
   If the user did NOT specify, pick flux-kontext + 3d, announce the pick,
   proceed unless they object.

4. **Run `stylize.py`**:
   ```bash
   python3 stylize.py <saved-photo> --style <style> --model <model> \
       --out assets/hero/hero-<slug>/avatar.png
   ```

5. **Show the avatar back to the user** via `reply(files=[...])` and confirm
   before spending Seedance money. "Нравится? Или сгенерировать в другом
   стиле / другой моделью?"

6. **Only AFTER the user approves the avatar** do you proceed to Seedance
   image-to-video with `assets/hero/hero-<slug>/avatar.png` as the hero.

**Escape hatch**: if the user EXPLICITLY says "send my real photo anyway, I
understand it may be rejected" — then proceed with the raw photo and warn
there's no refund on rejected jobs. Never interpret silence as consent.

**Where this is NOT needed**: landscapes, products, food, abstract art,
AI-generated/cartoon images the user already has, animals. Those go straight
to Seedance.

---

## Two brains, one project

This repo has **two LLM entry points** — don't confuse them:

### 1. **You** (the Claude Code session) — interactive brain
- Active when the user talks via Telegram plugin or CLI
- Uses **your own session capacity** — NOT `ANTHROPIC_API_KEY`, NOT OpenRouter, NOT local Gemma
- Your job on a typical TG request:
  1. Read incoming messages + any `image_path` / `attachment_file_id`
  2. Save hero photos to `assets/hero/hero-live/` (or `hero-{YYYYMMDD-HHMM}/` for per-run snapshots)
  3. Save backgrounds to `assets/background/`
  4. Compose the Seedance 2.0 prompt yourself using one of the 24 skills in `../skills/`
  5. `curl` fal.ai directly (you know the endpoint: `https://fal.run/bytedance/seedance-2.0/text-to-video` or `.../image-to-video`)
  6. Download the mp4 → reply via Telegram with `files=[...]`
- **Default: never invoke `director.py`'s internal LLM agents when the user is talking to you live** — you are already smarter. Pass `--skill <dir>` to bypass the shot_designer + prompt_writer agents, OR skip director.py entirely and call fal directly.

### 2. **`director.py --mode=...`** — autonomous brain
- Active on **cron schedule** (24/7 content calendar) or explicit `--mode=` flag
- Uses one of:
  - `--mode=claude` → `ANTHROPIC_API_KEY`
  - `--mode=zero` → LM Studio / Ollama at `LMSTUDIO_URL`
  - `--mode=openrouter` → `OPENROUTER_API_KEY` (many `:free` models)
- Runs the full 5-agent pipeline: script_breakdown → shot_designer → prompt_writer → fal_runner → assembler

## ⚠️ Content moderation guardrails

Seedance 2.0 on fal rejects:
- **Real photos of minors** (anyone under 18) — including the user's own kids
- Real photos of identifiable public figures / celebrities
- NSFW, explicit violence, weapons in most contexts
- Third-party copyrighted material

When the user sends a real photo of a person — especially their children — and
asks to animate it, **do NOT send it directly to Seedance**. It will fail and
waste credit. Instead:

1. Stylize the photo first via `fal-ai/flux-kontext` or `fal-ai/nano-banana/edit`
   (both accept real photos for editing/stylization, unlike Seedance video).
   Prompt example: "Transform this into a 3D Pixar-style cartoon character,
   clean studio background, soft lighting."
2. Save the stylized output to `assets/hero/hero-{slug}/hero.png`.
3. Only then call Seedance `image-to-video` with the stylized image as
   `image_url`. The moderator sees clearly-illustrated input and passes.

Always explain this to the user in one sentence BEFORE the stylization step so
they don't think it's a bug when you detour.

## Guardrails

- **Never commit `.env`** — it's gitignored, keep it that way.
- **Never print full API keys** to chat. Show `<SET>` or `sk-…xxx` masked.
- **Always `--dry-run` first** when the user asks you to try something new — shows the plan without spending fal credit.
- **Before any paid fal call**, show the user payload + estimated cost and wait for confirmation (unless they explicitly said "go fast" or similar).
- **Hero/background asset writes**: put photos into `assets/hero/heroN/` or `assets/hero/hero-live/`. Never overwrite `assets/hero/heroN/` folders the user curated — make a new subfolder for session uploads.

## 🖼️ Когда приходит картинка — обязательный flow

Когда пользователь присылает изображение через Telegram (image_path в теге), **ВСЕГДА**
делай следующее — не жди команды, сам определяй и предлагай:

### Шаг 1 — Определи тип картинки (vision)
Посмотри на изображение и определи:
- **face-cartoon** — мультяшное/AI лицо (аватар девочек, Pixar-стиль и т.д.)
- **face-real** — реальное фото человека → сначала stylize.py, см. HARD RULE #1
- **landscape** — пейзаж, город, природа, архитектура
- **product** — товар, объект, еда
- **abstract** — паттерн, текстура, арт

### Шаг 2 — Предложи 3 сценария из календаря
Подбери 3 подходящих слота из CALENDAR_META в director.py и ответь примерно так:

```
Вижу [тип]. Вот 3 сценария под эту картинку:

1️⃣ [h14] Rendered Reality — 3D CGI, Pixar-герой, fal-wan26, ~$0.30
   "Твой аватар в студийном 3D освещении, медленный облёт камеры"

2️⃣ [h21] Bedtime Chaos — мультфильм/bedtime, fal-wan26, ~$0.30
   "Мягкие цвета, герой засыпает, звёзды появляются"

3️⃣ [h16] Rush Hour Clash — аниме-экшн, fal-wan26, ~$0.25
   "Атака, спецприём, искры, скорость"

Выбери номер — или скажи свою идею.
🎵 Добавить звук? Три варианта:
• Пришли аудио файл (музыка / голос) — Wan наложит его
• Надиктуй голосовое сообщение — я транскрибирую и сделаю TTS
• Напиши текст что должен говорить герой — сделаю TTS и передам Вану
• "Без звука" — тишина
```

### Шаг 3 — Спроси про аудио (Wan поддерживает!)
Wan 2.5/2.6 принимает `audio_url` — фоновая музыка или речь для липсинка.
Четыре варианта от пользователя:

| Что прислал | Что делать |
|---|---|
| Аудио файл (mp3/wav/ogg) | Скачай через `download_attachment` → загрузи на fal storage → `audio_url` |
| Голосовое сообщение (voice) | Скачай → конвертируй в mp3 (ffmpeg) → загрузи на fal storage → сразу как `audio_url` в видео. Без транскрипции, без TTS — твой голос напрямую. |
| Текст ("скажи: Привет мир") | Синтез через `fal-ai/minimax-tts` или `fal-ai/fish-speech` → `audio_url` |
| "Без звука" / молчание | Не добавляй `audio_url` |

Стоимость TTS: ~$0.03/строку (minimax) — сообщи пользователю перед генерацией.

**Формат ответа боту должен включать:**
1. Что ты видишь на картинке (1 строка)
2. 3 сценария с ценой
3. Вопрос про музыку/речь
4. Никаких лишних вопросов — всё в одном сообщении

## Typical TG request → action map

| User says | You do |
|---|---|
| `[фото]` (просто картинка без текста) | Анализируй → предложи 3 сценария + спроси про аудио |
| `[фото] + номер сценария` | Сразу рендери выбранный сценарий, спроси только про аудио |
| `[фото1] hero 3D cartoon [фото2] background — generate` | Save photos → compose prompt → fal image-to-video → return mp4 |
| "чек" / "flight check" | Run `director.py --mode=openrouter --hour $(date +%H) --dry-run` |
| "h14 test" | One-shot render через `--confirm`, показать payload, ждать y/N |
| "h14 go" | Рендер без confirm (пользователь принял риск) |
| "статус" / "status" | `ls -lt output/*.mp4 \| head -5`, git log -3, fal balance |

## Verified facts

- fal.ai Seedance 2.0 endpoints: `https://fal.run/bytedance/seedance-2.0/text-to-video` and `/image-to-video` (NOT `fal-ai/seedance/v2/...`)
- Auth header: `Authorization: Key $FAL_KEY`
- Enhancor API requires Creator subscription ($344+/yr) — not pay-as-you-go. Prefer fal for new users.
- LM Studio `/v1/chat/completions` is the safest OpenAI-compat path; `/v1/responses` is newer and may not be in every local model's support matrix.
