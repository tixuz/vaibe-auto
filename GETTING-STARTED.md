# vaibe-auto — 10-Minute Setup (One Page)

Work top to bottom. Tick each box. Stop at "You're done."

---

## ⚠️ Content policy — READ FIRST

Seedance 2.0 (and ALL major video generators — Veo, Runway, Kling, Luma)
reject real photos of:

- **Minors / children** — even your own kids. Real faces of anyone under 18
  will be rejected, often without a helpful error.
- **Identifiable public figures / celebrities.**
- **NSFW / violence / weapons** in most contexts.
- **Photos you don't have rights to.**

### Workaround for your own kids' photos (the common case)

Don't send real photos to `--provider fal`. Instead:

1. **Stylize the photo first** with an image-to-image model that allows it:
   - `fal-ai/flux-kontext` — edit-by-prompt, supports "turn into 3D cartoon"
   - `fal-ai/nano-banana/edit` — Google's Nano Banana image editor
   - Open-source local: ComfyUI + IP-Adapter / InstantID + style LoRA
2. Save the **stylized** output as `assets/hero/heroN/*.png`
3. NOW send THAT (the cartoon/3D version) as the hero reference — moderation
   passes because the input is clearly illustrated, not photographic

Ask me in TG: **"стилизуй это фото в 3D мультяшный стиль"** (attach photo)
and I'll do step 1 for you via `flux-kontext` before touching Seedance.

---

## 1. System prerequisites

- [ ] **Python ≥ 3.11** — check: `python3 --version`
- [ ] **git** — check: `git --version`
- [ ] **ffmpeg** (stitches the clips) — macOS: `brew install ffmpeg` • Ubuntu: `sudo apt install ffmpeg`
- [ ] Clone the repo
  ```bash
  git clone https://github.com/tixuz/vaibe-auto.git
  cd vaibe-auto
  cp .env.example .env
  ```

---

## 2. Pick ONE brain (LLM) — then you can always add the other later

### 🅰️ Claude mode (paid, highest quality — "douchebag edition")
- [ ] Have an **Anthropic API key**? → https://console.anthropic.com/
- [ ] Put it in `.env`:
  ```
  ANTHROPIC_API_KEY=sk-ant-...
  ANTHROPIC_MODEL=claude-haiku-4-5
  ```
- [ ] Run flag will be `--mode=claude`. **Done with section 2.**

### 🅲 OpenRouter mode (hybrid — many FREE models + paid premium in one API)
One account, one key, 100+ models (Claude, GPT, Gemini, DeepSeek, Qwen, Llama, ...).
Free tier models have `:free` suffix — zero cost, just rate-limited (~20 req/min).

- [ ] Account → https://openrouter.ai/keys → **Create Key**
- [ ] (Optional) add $5-10 for paid models; free tier works without billing
- [ ] `.env`:
  ```
  OPENROUTER_API_KEY=sk-or-v1-...
  OPENROUTER_MODEL=deepseek/deepseek-chat-v3:free
  ```
- [ ] Good free models to pick: `deepseek/deepseek-chat-v3:free`,
      `qwen/qwen-2.5-72b-instruct:free`, `google/gemini-2.0-flash-exp:free`
- [ ] Run flag: `--mode=openrouter`. **Done with section 2.**

### 🅱️ Zero mode (free, fully local — no internet after setup)
Runs a local LLM on your machine. Two install paths — pick one:

**Path B1 — LM Studio (recommended, GUI, zero config)**
- [ ] Download LM Studio → https://lmstudio.ai/
- [ ] In LM Studio: search + download `Qwen2.5-7B-Instruct` (alias **Miniqwen** in our docs)
- [ ] Start the **Local Server** tab → click **Start Server** (defaults to `http://localhost:1234`)
- [ ] Run flag will be `--mode=zero`. **Done with section 2.**

**Path B2 — Docker (for headless servers)**
- [ ] `docker --version` works
- [ ] Run Ollama with an OpenAI-compatible shim:
  ```bash
  docker run -d --name vaibe-llm -p 1234:11434 \
    -v ollama:/root/.ollama ollama/ollama
  docker exec vaibe-llm ollama pull qwen2.5:7b-instruct
  ```
- [ ] Put in `.env`:
  ```
  LMSTUDIO_URL=http://localhost:1234/v1/chat/completions
  LMSTUDIO_MODEL=qwen2.5:7b-instruct
  ```
- [ ] Run flag will be `--mode=zero`. **Done with section 2.**

---

## 3. Video renderer — pick ONE provider (always required)

### 🅰️ fal.ai (default, simplest)
- [ ] Account → https://fal.ai/dashboard/keys → add billing
- [ ] Price: ~$0.10–0.50 per 6s clip
- [ ] `.env`:  `FAL_KEY=fal-...`
- [ ] Run flag: `--provider fal` (or omit — it's the default)

### 🅱️ Enhancor.ai — ⚠️ requires paid subscription, NOT pay-as-you-go
Same Seedance 2.0 model, advertised at up to −75% per-second cost. **But the
API Dashboard is gated behind the Creator plan ($459/yr, or $344 first year
with SAVE25).** Without that subscription the API is simply unavailable.

Only worth it if you're already committed to heavy daily generation and have
done the math:

| Daily volume | fal.ai pay-as-you-go | Enhancor Creator |
|---|---|---|
| 2–3 clips/day | ~$300–500/yr | $344 sub **alone**, before any clip |
| 20+ clips/day | ~$2,500+/yr | $344 sub + cheaper per-clip → **can win** |

- [ ] Still interested? Subscribe → https://app.enhancor.ai/subscription
- [ ] Unlock API Dashboard → https://app.enhancor.ai/api-dashboard
- [ ] `.env`:
  ```
  ENHANCOR_API_KEY=...
  ENHANCOR_PROMO=SAVE25
  ```
- [ ] Run flag: `--provider enhancor`

> ℹ️ **Disclosure:** `SAVE25` was promoted by Sirio Berati and is very likely
> his affiliate code (Enhancor pays him a kickback). The discount itself is
> real on the first subscription year; his "up to −75% off API" claim
> conveniently omits that the API requires a $344+/yr subscription to unlock.
> For most beginners, **stay on fal.ai** — zero commitment, no subscription.

### Sanity check either one
```bash
# fal
curl -sS -H "Authorization: Key $FAL_KEY" https://fal.run/health || echo "check key"
# enhancor
curl -sS -H "Authorization: Bearer $ENHANCOR_API_KEY" https://api.enhancor.ai/v1/health || echo "check key"
```

---

## 4. Assets — where your hero photos and backgrounds live

vaibe-auto looks inside two folders in the repo:

```
assets/
├── hero/
│   ├── hero1/   ← one hero per subfolder, any .jpg/.png/.webp
│   ├── hero2/
│   └── hero3/   ← add as many heroN folders as you want
└── background/  ← drop backgrounds here
```

How the picker works:
- `--hour 03` → picks `hero/hero{(3 % N)+1}/` → first image in that folder
- Backgrounds: first image in `assets/background/` is used for every run
- Hero image is sent to fal.ai as `@Image1` (image-to-video). No hero = text-to-video.

### Option A — local folders (simplest)
- [ ] Drag your photos into `assets/hero/hero1/`, `hero2/`, etc.
- [ ] Drag backgrounds into `assets/background/`

### Option B — sync from Google Drive / Photos
- [ ] Install [rclone](https://rclone.org/) → `brew install rclone` (or apt)
- [ ] `rclone config` → add a remote called `gdrive` (OAuth to your Google account)
- [ ] In Google Drive, make a folder `vaibe-assets/hero/hero1/`, etc., upload your photos there
- [ ] Mount it into the repo:
  ```bash
  rclone mount gdrive:vaibe-assets ./assets --vfs-cache-mode writes &
  ```
- [ ] Now every photo you drop in Drive appears in `assets/` — works for Google Photos too if you export an album to a Drive folder.

### Option C — Dropbox / iCloud / SMB
Same idea: mount the network folder at `./assets/`. vaibe-auto doesn't care what's behind it.

---

## 4.5 🎭 Real people in your photos? Make avatars FIRST

Re-read section "⚠️ Content policy" at the top if you haven't. **Real photos
of your kids, family, yourself, or any identifiable person will be rejected
by Seedance** — the safest workflow is to generate a stylized avatar once,
save it, reuse forever.

### Recommended workflow — "Avatar-first"

- [ ] **Step 1: pick the best source photos** (one per person, clear face, good lighting)
- [ ] **Step 2: stylize each photo ONCE with `stylize.py`**:
  ```bash
  # Turn daughter's photo into a 3D Pixar-style avatar
  python3 stylize.py ~/Photos/lena.jpg --style 3d \
      --out assets/hero/lena/avatar.png

  # Turn son's photo into an anime avatar
  python3 stylize.py ~/Photos/artem.jpg --style anime \
      --out assets/hero/artem/avatar.png

  # Yourself as a comic hero
  python3 stylize.py ~/Photos/me.jpg --style comic \
      --out assets/hero/me/avatar.png
  ```
  Each `stylize.py` call costs ~$0.04 via fal-ai/flux-kontext. One-time spend.

- [ ] **Step 3a: pick a style preset** (or pass a full custom prompt):

  | `--style` | Look |
  |---|---|
  | `3d` *(default)* | Pixar-style 3D cartoon, soft rim light, wholesome |
  | `anime` | Studio Ghibli cel-shade, pastel background |
  | `comic` | Western comic book, bold ink + halftone |
  | `disney` | Disney 2D animated, vibrant flat colors |
  | `claymation` | Aardman-style clay, fingerprint texture |
  | *(custom)* | Pass any string: `--style "Pixar 3D, rainbow hair, studio"` |

- [ ] **Step 3b: pick an image-edit model** (`--model ...`):

  | `--model` | Price | Best for |
  |---|---|---|
  | `flux-kontext` *(default)* | ~$0.04 | balanced quality, most reliable |
  | `flux-kontext-max` | ~$0.08 | highest fidelity, 2× price |
  | `nano-banana` | ~$0.04 | Google's model, strong face preservation |
  | `seededit` | ~$0.03 | cheapest, ByteDance, quick iterations |
  | `qwen-edit` | ~$0.03 | open-weights, great for anime/manga |
  | `ideogram` | ~$0.06 | best if your avatar needs text/logos |
  | `gpt-image` | ~$0.07 | OpenAI (via BYOK), distinctive style |

  ```bash
  # Try two models cheap, keep the one you like
  python3 stylize.py lena.jpg --style 3d --model seededit     --out /tmp/a.png
  python3 stylize.py lena.jpg --style 3d --model nano-banana  --out /tmp/b.png
  open /tmp/a.png /tmp/b.png   # pick winner, copy to assets/hero/lena/
  ```

- [ ] **Step 4: use the avatar as hero from now on**:
  ```bash
  python3 director.py --hour 14 --provider fal --confirm
  # picks assets/hero/hero{N}/ automatically — or force a specific avatar:
  #   ln -s assets/hero/lena /path  or just rename folder to heroN/
  ```

- [ ] **Step 5: ask me to do it in TG** (if Claude Code + Telegram is running):
  > *[attach daughter's photo]* "сделай 3D аватар и используй его как героя"
  >
  > I'll detect the real face, run `stylize.py` first, save to
  > `assets/hero/hero-live/`, confirm with you, then feed the avatar to
  > Seedance. No direct real-photo upload to video API.

### When you don't need avatars

- Landscapes, products, food, abstract shots → send the photo straight to
  Seedance, it's fine.
- AI-generated / cartoon / illustration you already have → also fine.
- Photos of animals (your cat, dog) → usually fine, but stylize if you want
  consistent character across many clips.

### Cost summary for the avatar path

| Step | Tool | Cost |
|---|---|---|
| Stylize 1 photo → avatar PNG | `stylize.py` (fal flux-kontext) | ~$0.04 |
| Reuse avatar for N videos | free (it's just a PNG in your folder) | $0 |
| Video per clip | director.py + fal Seedance 2.0 | ~$0.10-0.50 |

---

## 5. First run (always do `--dry-run` first — no fal.ai money spent)

- [ ] Plan-only test:
  ```bash
  python3 director.py --mode=zero --hour 10 --dry-run
  ```
  You should see `[assets] hero -> ...`, `[plan] output/…plan.json`, and no errors.
- [ ] Full render with **payload preview** (stops before each paid call):
  ```bash
  python3 director.py --mode=zero --hour 10 --provider fal --confirm
  ```
  You'll see the JSON payload + target URL, type `y` to spend money, `N` to abort.
- [ ] Full render, no prompts (burns credit, ~$0.10–0.50):
  ```bash
  python3 director.py --mode=zero --hour 10 --provider fal
  ```
  Final video lands in `output/<timestamp>-h10-golden-window.final.mp4`.

---

## 6. Go 24/7 — the content calendar

Each hour maps to a **catchy theme + skill** (see README.md for the full table).
Run one video every hour via cron:

- [ ] `crontab -e` then add:
  ```cron
  0 * * * * cd /ABSOLUTE/PATH/vaibe-auto && \
    /usr/bin/env python3 director.py --mode=zero --provider fal \
    --hour $(date +\%H) >> logs/cron.log 2>&1
  ```
- [ ] Verify after one hour: `ls output/*.final.mp4`

## 7. You're done.

| Check | Command |
|---|---|
| LLM reachable | `curl -sS localhost:1234/v1/models` (zeroclaw) or `echo $ANTHROPIC_API_KEY` (claude) |
| fal.ai key set | `echo $FAL_KEY` |
| Heroes present | `ls assets/hero/hero1/` |
| ffmpeg works | `ffmpeg -version \| head -1` |
| Dry-run works | `python3 director.py --mode=zero --hour 7 --dry-run` |

If any row fails, jump back to that section above.

---

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| `LM Studio unreachable` | Start LM Studio → Local Server → Start Server |
| `ANTHROPIC_API_KEY not set` | `source .env` or `export ANTHROPIC_API_KEY=...` |
| `fal.ai returned no video URL` | Check credit balance on fal.ai dashboard |
| `ffmpeg: command not found` | `brew install ffmpeg` |
| Hero not detected | File must be `.jpg/.jpeg/.png/.webp` inside `assets/hero/heroN/` |
| Weird JSON errors (zeroclaw only) | Re-run once, or switch that slot to `--mode=claude` |
