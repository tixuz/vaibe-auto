# vaibe-auto — Multi-Agent AI Film Director

**vaibe** = **V**ideo + **A**I + **I**mproved/**I**ntelligent + **B**etter + **E**dits.
**auto** = hands-off, cron-friendly, 24/7.

Pronounced like "vibe" but spelled with the letters that mean something — your
vibe, auto-edited better by AI into video.

### Userstory

> As a creator who wants a TikTok-style 24/7 video channel without paying
> someone else's bill or hiring an editor, I run `vaibe-auto` on an hourly cron.
> It **V**ideos the idea, **A**I-breaks it into shots, picks **I**mproved
> **B**etter **E**dit patterns from 24 skills, and **auto**-assembles the cut.
> Douchebag mode uses Claude. Zerodouche mode uses local Miniqwen. Both feed
> fal.ai Seedance 2.0. I wake up to 24 finished clips.

---

A self-hosted multi-agent director that uses our 24 Seedance 2.0 skills +
fal.ai, with **two modes** so you can pick your pain:

| Mode | Who | Cost | Quality | LLM |
|---|---|---|---|---|
| `--mode=claude` | Douchebags (с деньгами) | ~$0.02 LLM + fal.ai | Top | Anthropic API (Haiku/Sonnet) |
| `--mode=zeroclaw` | Zerodouches (полный ноль) | **$0.00 LLM** + fal.ai | Good | LM Studio / Miniqwen (local) |

fal.ai video cost stays the same (~$0.10-0.50 per clip). The LLM is the only
thing that changes between modes.

## Pipeline

```
story → script_breakdown → [shot_designer → prompt_writer] × N → fal_runner × N → assembler → final.mp4
         (1 LLM call)      (2 LLM calls per shot)                  (fal.ai)        (ffmpeg)
```

5 agents, all swappable between Claude and Miniqwen via the `LLM` class.

## Quickstart

### Douchebag mode (Claude)
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export FAL_KEY=fal-...
python director.py --mode=claude --story "A samurai meets an AI in Tokyo rain."
```

### Zerodouche mode (Miniqwen local)
```bash
# 1. Start LM Studio, load Miniqwen (use /lm-studio skill)
# 2. Ensure localhost:1234 is live
export FAL_KEY=fal-...
python director.py --mode=zeroclaw --story "A cat discovers ikigai at dawn."
```

### 24-hour calendar slot
```bash
python director.py --mode=zeroclaw --hour 3   # Ghost Protocol (character consistency)
python director.py --mode=claude  --hour 22   # Last Round (fight scenes)
```

### Dry run (plan only, no video)
```bash
python director.py --mode=zeroclaw --story "..." --dry-run
```

## 24-Hour Content Calendar

Catchy name per hour, mapped to one of the 24 skills:

| Hour | Name | Skill |
|-----:|------|-------|
| 00 | Midnight Silk | 21-asmr-ambient |
| 01 | 3AM Dread | 19-horror-thriller |
| 02 | Sleepless Confessions | 16-short-drama |
| 03 | Ghost Protocol | 18-character-consistency |
| 04 | Blue Hour Drift | 20-travel-landscape |
| 05 | Dawn Dispatch | 22-news-documentary |
| 06 | First Light Lesson | 17-educational |
| 07 | Morning Ritual | 14-food-beverage |
| 08 | Origin Story | 12-brand-story |
| 09 | 9 to Thrive | 06-motion-design-ad |
| 10 | Golden Window | 01-cinematic |
| 11 | Scroll Breaker | 11-social-hook |
| 12 | Lunch Impulse | 07-ecommerce-ad |
| 13 | The Reveal | 09-product-360 |
| 14 | Rendered Reality | 02-3d-cgi |
| 15 | Afternoon Beat | 10-music-video |
| 16 | Rush Hour Clash | 08-anime-action |
| 17 | Golden Hour Fit | 13-fashion-lookbook |
| 18 | End of Day Grind | 23-sports-action |
| 19 | Dream Door | 15-real-estate |
| 20 | Panel Explosion | 04-comic-to-video |
| 21 | Bedtime Chaos | 03-cartoon |
| 22 | Last Round | 05-fight-scenes |
| 23 | Night Render | 24-fal-runner |

## Automate 24/day via cron

```cron
0 * * * * cd /Users/khindol/webstore/utils/ai-video-skills/zopia-clone && \
  /usr/bin/env python3 director.py --mode=zeroclaw --hour $(date +\%H) >> logs/cron.log 2>&1
```

## Cost math (per day, 24 clips)

| Mode | LLM | fal.ai | Total |
|---|---|---|---|
| zeroclaw | $0.00 | $2.40-12.00 | **$2.40-12.00** |
| claude (Haiku) | ~$0.50 | $2.40-12.00 | ~$2.90-12.50 |

## Files

- `director.py` — orchestrator + 5 agents + LLM wrapper
- `output/*.plan.json` — shot breakdown + prompts (audit trail)
- `output/*.final.mp4` — assembled videos
- `logs/*.log` — full prompt/reply traces for every LLM call

## Agent roles

1. **script_breakdown** — story → 3-5 shots (JSON)
2. **shot_designer** — picks skill (01-24) per shot
3. **prompt_writer** — applies SKILL.md, produces fal.ai-ready prompt
4. **fal_runner** — calls fal.ai Seedance 2.0, downloads mp4
5. **assembler** — ffmpeg concat → final

## Troubleshooting

- **LM Studio unreachable**: use `/lm-studio` skill to load Miniqwen.
- **fal.ai returns no URL**: verify `FAL_KEY` and that you have credit.
- **ffmpeg missing**: `brew install ffmpeg` — or use `--dry-run`.
- **JSON parse errors in zeroclaw mode**: Miniqwen is chattier — the extractor
  strips code fences and grabs the first `{...}`/`[...]`. If it still fails,
  re-run (temperature 0.7) or switch that single run to `--mode=claude`.
