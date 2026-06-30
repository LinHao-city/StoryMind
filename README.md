<p align="center">
  <img src="assets/logo.png" alt="OpenMontage" width="200">
</p>

<h1 align="center">OpenMontage</h1>

<p align="center"><strong>An open-source, agentic AI video production system.</strong></p>

<p align="center">
  <a href="#start-from-a-video-you-already-love">Paste A Video</a> &nbsp;·&nbsp;
  <a href="#quick-start">Quick Start</a> &nbsp;·&nbsp;
  <a href="#try-these-prompts">Try These Prompts</a> &nbsp;·&nbsp;
  <a href="#pipelines">Pipelines</a> &nbsp;·&nbsp;
  <a href="#how-it-works">How It Works</a> &nbsp;·&nbsp;
  <a href="docs/PROVIDERS.md">Providers</a> &nbsp;·&nbsp;
  <a href="AGENT_GUIDE.md">Agent Guide</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPLv3-blue.svg" alt="License"></a>
</p>

---

Turn your AI coding assistant into a full video production studio. Describe what you want in plain language — your agent handles research, scripting, asset generation, editing, and final composition.

**Important distinction:** OpenMontage can make image-based videos, but it can also make a real **video video** for free/open-source workflows: the agent builds a corpus from free stock footage and open archives, retrieves actual motion clips, edits them into a timeline, and renders a finished piece. That is not the usual "animate a handful of stills and call it video" trick.

<div align="center">
  <video src="https://github.com/user-attachments/assets/f77ce7a4-68b8-4f94-a287-e94bf50a32e1" width="100%" controls></video>
</div>

> **"SIGNAL FROM TOMORROW"** — a cinematic sci-fi trailer fully produced through OpenMontage: concept, script, scene plan, Veo-generated motion clips, soundtrack, and Remotion composition.

<div align="center">
  <video src="https://github.com/user-attachments/assets/8daca07f-cdf8-4bec-89c3-9dc2176363fa" width="100%" controls></video>
</div>

> **"THE LAST BANANA"** — a 60-second Pixar-style animated short about a lonely banana who finds friendship with a kiwi. 6 Kling v3-generated motion clips (via fal.ai), narration, royalty-free piano music, TikTok-style word-level captions, and Remotion composition. Total cost: **$1.33**.

<div align="center">
  <video src="https://github.com/user-attachments/assets/e03b5d1f-1199-4093-9f31-a43aa9da2c68" width="100%" controls></video>
</div>

> **"The Library at Alexandria"** — a 70-second history elegy. Five hand-authored scenes set to narration and a free Pixabay strings score. Total cost: **$0.02**. Built through OpenMontage's atelier (bespoke) composition mode.

<div align="center">
  <video src="https://github.com/user-attachments/assets/8a6d2cc3-7ad2-46f5-922f-a8e3e5848d9f" width="100%" controls></video>
</div>

> **"VOID — Neural Interface"** — a product ad produced with just one API key. 4 AI-generated images, TTS narration, auto-sourced royalty-free music, word-level subtitles, and Remotion data visualizations. Total cost: **$0.69**.

<div align="center">
  <video src="https://github.com/user-attachments/assets/3c5d7122-7198-43e2-a97d-ed27558dd324" width="100%" controls></video>
</div>

> **"Afternoon in Candyland"** — a Ghibli-style anime animation. 12 FLUX-generated images with multi-image crossfade, cinematic camera motion, sparkle/petal/firefly particle overlays, and ambient music. Total cost: **$0.15**.

<div align="center">
  <video src="https://github.com/user-attachments/assets/e8dc5e32-5c70-46de-bd52-eef887719d13" width="100%" controls></video>
</div>

> **"Mori no Seishin"** — a Ghibli-style anime animation of a forest spirit's journey through ancient woods. 12 FLUX-generated images with parallax crossfade, drift and pan camera motion, firefly and petal particles, cinematic vignette lighting, and ambient forest soundtrack. Total cost: **$0.15**.

---

## Start From A Video You Already Love

Starting from a reference video is often faster than starting from a blank prompt.

OpenMontage can start from a **YouTube video, Short, Reel, TikTok, or local clip** and turn it into a grounded production plan:

1. **Paste a reference video**
2. **The agent analyzes transcript, pacing, scenes, keyframes, and style**
3. **You get 2-3 differentiated concepts, an honest tool path, cost estimates, and a sample before full production**

```text
"Here's a YouTube Short I love. Make me something like this, but about quantum computing."
```

What you get back is not "best guess prompt spaghetti." You get:

- **What it keeps** from the reference: pacing, hook style, structure, tone
- **What it changes**: topic, visual treatment, angle, narration approach
- **What it will cost** at your target duration, before asset generation starts
- **What it will actually look like** with your currently available tools

Works with **Claude Code, Cursor, Copilot, Windsurf, Codex** — any AI coding assistant that can read files and run code.

---

## Quick Start

### Prerequisites

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **FFmpeg** — see platform instructions below
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **An AI coding assistant** — Claude Code, Cursor, Copilot, Windsurf, or Codex

**FFmpeg installation by platform:**

```bash
# Windows (recommended)
winget install --id Gyan.FFmpeg --source winget

# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### Install & Run

```bash
git clone https://github.com/LinHao-city/OpenMontage.git
cd OpenMontage

# Linux / macOS
make setup

# Windows — no make? Run manually:
pip install -r requirements.txt
cd remotion-composer && npm install && cd ..
pip install piper-tts
cp .env.example .env
```

Open the project in your AI coding assistant and tell it what you want:

```
"Make a 60-second animated explainer about how neural networks learn"
```

Or if you want the real-footage path:

```text
"Make a 75-second documentary montage about city life in the rain. Use real footage only, no narration, elegiac tone, with music."
```

That's it. The agent researches your topic with live web search, generates AI images, writes and narrates the script with voice direction, finds royalty-free background music automatically, burns in word-level subtitles, and renders the final video. Before you see anything, the system runs a multi-point self-review — ffprobe validation, frame sampling, audio level analysis, delivery promise verification, and subtitle checks.

> **Windows note:** If `npm install` fails with `ERR_INVALID_ARG_TYPE`, use `npx --yes npm install` instead.  
> **Piper TTS on Windows:** Voice models are auto-downloaded to `%USERPROFILE%\.piper\models` on first use.

### Quick Capability Check

After setup, verify everything is running:

```bash
python -c "from tools.tool_registry import ToolRegistry; reg = ToolRegistry(); reg.discover(); avail = [n for n in reg.list_all() if reg.get(n).get_status().value == 'available']; print(f'{len(avail)} tools available')"
```

### Add API Keys (optional — more keys = more tools)

```bash
# .env — every key is optional, add what you have

# NetEase Leihuo Gateway (video, image, TTS via Doubao + Mimo):
LEIHUO_API_KEY=your-key
LEIHUO_BASE_URL=https://ai.leihuo.netease.com/v1
# For Claude models via Leihuo — must use Anthropic SDK format:
ANTHROPIC_BASE_URL=https://ai.leihuo.netease.com/
ANTHROPIC_AUTH_TOKEN=your-key

# Free stock media:
PEXELS_API_KEY=your-key        # Free — https://www.pexels.com/api/
PIXABAY_API_KEY=your-key       # Free — https://pixabay.com/api/docs/
UNSPLASH_ACCESS_KEY=your-key   # Free — https://unsplash.com/developers

# Image + video gateway (international):
FAL_KEY=your-key               # FLUX images + Google Veo, Kling, MiniMax video

# Voice & images:
ELEVENLABS_API_KEY=your-key    # Premium TTS, AI music, sound effects
OPENAI_API_KEY=your-key        # OpenAI TTS, DALL-E 3 images
XAI_API_KEY=your-key           # xAI Grok image edits/generation + video
GOOGLE_API_KEY=your-key        # Google Imagen images, Google TTS (700+ voices)

# More video providers:
HEYGEN_API_KEY=your-key        # HeyGen — VEO, Sora, Runway, Kling via single gateway
RUNWAY_API_KEY=your-key        # Runway Gen-4 direct

# Music:
SUNO_API_KEY=your-key          # Full songs, instrumentals, any genre
```

<details>
<summary><strong>Have a GPU? Unlock free local video generation</strong></summary>

```bash
# Linux / macOS
make install-gpu

# Windows
pip install -r requirements-gpu.txt

# Then add to .env:
VIDEO_GEN_LOCAL_ENABLED=true
VIDEO_GEN_LOCAL_MODEL=wan2.1-1.3b  # or wan2.1-14b, hunyuan-1.5, ltx2-local, cogvideo-5b
```

</details>

---

## What You Get With Zero API Keys

You don't need paid API keys to make real videos. Out of the box, setup gives you:

| Capability | Free Tool | What It Does |
| ---------- | --------- | ------------ |
| **Narration** | Piper TTS | Free offline text-to-speech — real human-sounding narration |
| **Open footage** | Archive.org + NASA + Wikimedia Commons | Free/open archival footage, educational media, and documentary texture |
| **Extra stock** | Pexels + Unsplash + Pixabay | Free stock footage/images (developer keys are free to get) |
| **Composition (React)** | Remotion | React-based rendering — spring-animated image scenes, text cards, stat cards, charts, TikTok-style word-level captions, TalkingHead |
| **Composition (HTML/GSAP)** | HyperFrames | HTML/CSS/GSAP rendering — kinetic typography, product promos, launch reels, registry blocks, website-to-video, rigged SVG character animation |
| **Post-production** | FFmpeg | Encoding, subtitle burn-in, audio mixing, color grading |
| **Subtitles** | Built-in | Auto-generated captions with word-level timing |
| **AI Storyboarding** | StoryboardPlanner | LLM-powered shot decomposition with cinematography language |

**Two free-ish paths:**

- **Image-based video:** Piper narrates your script, images provide the visuals, and Remotion animates them into a polished edit.
- **Local character animation:** SVG rigs, pose libraries, GSAP timelines, and HyperFrames render cartoon character acting to `projects/<project-name>/renders/final.mp4`.
- **Real-footage video:** the documentary montage pipeline builds a CLIP-searchable corpus from Archive.org, NASA, Wikimedia Commons, and optional free-key sources like Pexels and Unsplash, then cuts together actual motion footage into a finished video.

If you want the second one, prompt for a **documentary montage**, **tone poem**, or **stock-footage collage**, and explicitly say **use real footage only**.

---

## Try These Prompts

Copy any of these into your AI coding assistant after setup. Each one runs a full production pipeline.

### Start from a reference video

> "Here's a YouTube short I love. Make me something like this, but about CRISPR for high school students."

> "Analyze this Reel and give me 3 original variants I could make for my own product launch."

> "I like the pacing and hook in this video. Keep that energy, but turn it into a 45-second explainer about black holes."

### Zero keys needed

> "Make a 45-second animated explainer about why the sky is blue"

> "Create a 60-second video about the history of the internet, with narration and captions"

> "Make a data-driven explainer about coffee consumption around the world"

### Free real-footage documentary path

> "Make a 90-second documentary montage about what a city feels like at 4am. Use real footage only, no narration, elegiac tone."

> "Create a 60-second Adam-Curtis-style archival collage about 1950s consumer optimism. Prefer Archive.org and Wikimedia footage."

> "Cut together a dreamlike montage about coming home in the rain using real stock footage only. Music yes, narration no."

### With an image/video provider configured (~$0.15–$1.50)

> "Create a 30-second Ghibli-style animated video of a magical floating library in the clouds at golden hour"

> "Make a 30-second anime-style animation of an underwater temple with bioluminescent coral and ancient ruins"

> "Create an animated explainer about how CRISPR gene editing works, using AI-generated visuals"

> "Make a product launch teaser for a fictional smart water bottle called AquaPulse"

### Full setup (~$1–$3)

> "Create a cinematic 30-second trailer for a sci-fi concept: humanity receives a warning from 1000 years in the future"

> "Make a 90-second animated explainer about quantum computing for middle school students, with a fun narrator voice and custom soundtrack"

Want more? See the full **[Prompt Gallery](PROMPT_GALLERY.md)** for tested prompts with expected costs and output examples, or run `make demo` (Linux/macOS) to render zero-key demo videos instantly.

---

## Pipelines

Each pipeline is a complete production workflow, from idea to finished video.

| Pipeline | What It Produces | Best For |
| -------- | ---------------- | -------- |
| **Animated Explainer** | AI-generated explainer with research, narration, visuals, music | Educational content, tutorials, topic breakdowns |
| **Animation** | Motion graphics, kinetic typography, animated sequences | Social media, product demos, abstract concepts |
| **Avatar Spokesperson** | Avatar-driven presenter videos | Corporate comms, training, announcements |
| **Cinematic** | Trailer, teaser, and mood-driven edits | Brand films, teasers, promotional content |
| **Clip Factory** | Batch of ranked short-form clips from one long source | Repurposing long content for social media |
| **Documentary Montage** | Thematic montage cut from a CLIP-indexed corpus of free stock footage and open archives | Video essays, mood pieces, real-footage videos without paid generation APIs |
| **Hybrid** | Source footage + AI-generated support visuals | Enhancing existing footage with graphics |
| **Localization & Dub** | Subtitle, dub, and translate existing video | Multi-language distribution |
| **Podcast Repurpose** | Podcast highlights to video | Podcast marketing, audiogram videos |
| **Screen Demo** | Polished software screen recordings and walkthroughs | Product demos, tutorials, documentation |
| **Talking Head** | Footage-led speaker videos | Presentations, vlogs, interviews |

Every pipeline follows the same structured flow:

```
storyboard_plan -> consistency_setup -> research -> proposal -> script -> scene_plan -> assets -> edit -> compose
```

Each stage has a dedicated **director skill** — a markdown instruction file that teaches the agent exactly how to execute that stage. The agent reads the skill, uses the tools, self-reviews, checkpoints state, and asks for human approval at creative decision points.

> **Web research is a first-class stage.** Before writing a single word of script, the agent searches YouTube, Reddit, Hacker News, news sites, and academic sources. It gathers data points, audience questions, trending angles, and visual references — then cites everything in a structured research brief.

---

## Why OpenMontage?

Most AI video tools give you a single clip from a prompt. OpenMontage gives you an **end-to-end production pipeline** — the same structured process a real production team follows, automated by your AI agent.

- **12 production pipelines** — explainers, talking heads, screen demos, cinematic trailers, animations, podcasts, localization, documentary montages, and more
- **55+ production tools** — spanning video generation, image creation, text-to-speech, music, audio mixing, subtitles, enhancement, analysis, and AI storyboard planning
- **AI-powered storyboard planning** — LLM decomposes scripts into professional shot plans with cinematography language (shot scale, camera movement, lighting), character consistency anchoring, and cross-shot visual continuity
- **Character consistency management** — CharacterSheet + SceneConsistencyTracker ensure the same character description propagates across every generated shot
- **Reference-driven creation** — paste a video you like and the agent turns it into a grounded, differentiated production plan
- **Real-footage documentary creation without paid video models** — build actual edited videos from free/open motion footage and archival sources
- **Live web research built in** — before writing a single word of script, the agent runs 15-25+ web searches across YouTube, Reddit, news sites, and academic sources
- **Both free/local AND cloud providers** — every capability supports open-source local alternatives alongside premium APIs
- **No vendor lock-in** — swap providers freely. The scored selector ranks every provider across 7 dimensions and picks the best match automatically
- **Production-grade quality gates** — delivery promise enforcement, pre-compose validation, mandatory post-render self-review
- **Budget governance built in** — cost estimation before execution, spend caps, per-action approval thresholds

---

## How It Works

OpenMontage uses an **agent-first architecture**. There is no code orchestrator. Your AI coding assistant IS the orchestrator.

```
You: "Make a cinematic sci-fi short about an alien signal"
 |
 v
StoryboardPlanner: decomposes script into 6 shots with
                   shot scale, camera movement, lighting, character anchors
 |
 v
SceneConsistencyTracker: registers style anchors from Shot 1,
                         propagates to all subsequent shots
 |
 v
Agent reads pipeline manifest (YAML) — stages, tools, review criteria, success gates
 |
 v
Agent reads stage director skill (Markdown) — HOW to execute each stage
 |
 v
Agent calls Python tools — scored provider selection ranks every tool across 7 dimensions
 |
 v
Agent self-reviews using reviewer skill — schema validation, playbook compliance, quality checks
 |
 v
Agent checkpoints state (JSON) — resumable, with decision log and cost snapshot
 |
 v
Agent presents for your approval — you stay in control at every creative decision
 |
 v
Pre-compose validation gate — delivery promise, slideshow risk, renderer governance
 |
 v
Render (Remotion or FFmpeg) — composition engine matched to visual grammar
 |
 v
Post-render self-review — ffprobe, frame extraction, audio analysis, promise verification
 |
 v
Final video output — only if self-review passes
```

**Python provides tools and persistence.** All creative decisions, orchestration logic, review criteria, and quality standards live in readable instruction files (YAML manifests + Markdown skills) that you can inspect and customize.

---

## Architecture

```
OpenMontage/
├── tools/              # 55+ Python tools (the agent's hands)
│   ├── video/          # Video gen tools (Leihuo Seedance, Pexels, etc.) + compose, stitch, trim
│   ├── audio/          # TTS providers (Leihuo Mimo, Piper) + music, mixing, enhancement
│   ├── graphics/       # Image gen tools (Leihuo SeeDream) + diagrams, code snippets, math
│   ├── planning/       # AI storyboard planning, character consistency, prompt enhancement
│   ├── enhancement/    # Upscale, bg remove, face enhance, color grade, InstantID (Phase 3)
│   ├── analysis/       # Transcription, scene detect, frame sampling
│   ├── avatar/         # Talking head, lip sync
│   └── subtitle/       # SRT/VTT generation
│
├── pipeline_defs/      # YAML pipeline manifests (v3.0 with storyboard planning stages)
├── skills/             # Markdown skill files (the agent's knowledge)
│   ├── pipelines/      # Per-pipeline stage director skills
│   ├── creative/       # Creative technique skills
│   ├── core/           # Core tool skills (incl. cinematography-director)
│   └── meta/           # Reviewer, checkpoint protocol
│
├── schemas/            # 15 JSON Schemas (contract validation)
├── styles/             # Visual style playbooks (YAML)
├── remotion-composer/  # React/Remotion video composition engine
├── lib/                # Core infrastructure (config, checkpoints, pipeline loader)
├── UPGRADE_PROGRESS.md # AI storyboarding upgrade roadmap and change log
└── tests/              # Contract tests, QA integration tests, eval harness
```

### Three-Layer Knowledge Architecture

```
Layer 1: tools/ + pipeline_defs/     "What exists" — executable capabilities + orchestration
Layer 2: skills/                     "How to use it" — OpenMontage conventions and quality bars
Layer 3: .agents/skills/             "How it works" — external technology knowledge packs
```

---

## Supported Providers

> **Full setup guide with pricing and free tiers:** [`docs/PROVIDERS.md`](docs/PROVIDERS.md)

<details>
<summary><strong>Video Generation — 15 providers</strong></summary>

| Provider | Type | Notes |
| -------- | ---- | ----- |
| **Doubao Seedance 2.0** | Cloud API | Via Leihuo gateway — cinematic quality, native audio |
| **Kling** | Cloud API | High quality, fast |
| **Runway Gen-4** | Cloud API | Cinematic quality |
| **Google Veo 3** | Cloud API | Long-form, cinematic. Via fal.ai or HeyGen |
| **Grok Imagine Video** | Cloud API | Strong reference-image video |
| **Higgsfield** | Cloud API | Multi-model orchestrator with Soul ID for character consistency |
| **MiniMax** | Cloud API | Cost-effective |
| **HeyGen** | Cloud API | Multi-model gateway |
| **WAN 2.1** | Local GPU | Free, 1.3B and 14B variants |
| **Hunyuan** | Local GPU | Free, high quality |
| **CogVideo** | Local GPU | Free, 2B and 5B variants |
| **LTX-Video** | Local GPU / Modal | Free locally, or self-hosted cloud |
| **Pexels** | Stock | Free stock footage |
| **Pixabay** | Stock | Free stock footage |
| **Wikimedia Commons** | Stock | Free/open stock footage and archival video |

</details>

<details>
<summary><strong>Image Generation — 11 tools/providers</strong></summary>

| Provider | Type | Notes |
| -------- | ---- | ----- |
| **Doubao SeeDream 5.0** | Cloud API | Via Leihuo gateway — high-resolution (≥2048×2048) |
| **FLUX** | Cloud API | State-of-the-art quality |
| **Google Imagen** | Cloud API | Imagen 4 |
| **Grok Imagine Image** | Cloud API | Strong image edits, style transfer |
| **DALL-E 3 / gpt-image-2** | Cloud API | OpenAI's image models |
| **Recraft** | Cloud API | Design-focused generation |
| **Local Diffusion** | Local GPU | Stable Diffusion, free |
| **Pexels** | Stock | Free stock images |
| **Pixabay** | Stock | Free stock images |
| **Unsplash** | Stock | Free stock images |
| **ManimCE** | Local | Mathematical animations |

</details>

<details>
<summary><strong>Text-to-Speech — 5 providers</strong></summary>

| Provider | Type | Notes |
| -------- | ---- | ----- |
| **Mimo TTS** | Cloud API | Via Leihuo gateway — **free**, Xiaomi voice design |
| **MiniMax Speech** | Cloud API | Via Leihuo gateway — high quality paid |
| **ElevenLabs** | Cloud API | Premium voice quality |
| **OpenAI TTS** | Cloud API | Fast, affordable |
| **Piper** | Local | Completely free, offline, Windows/Mac/Linux |

</details>

<details>
<summary><strong>AI Storyboard Planning (New)</strong></summary>

| Tool | What It Does |
| ---- | ------------ |
| **StoryboardPlanner** | LLM decomposes scripts into structured shot plans (shot scale, camera movement, lighting, character-injected prompts) |
| **CharacterSheet** | Registers characters with visual descriptions; auto-injects anchors into every shot prompt featuring that character |
| **SceneConsistencyTracker** | Propagates style/color/lighting anchors from Shot 1 across all subsequent shots (Jellyfish-inspired) |
| **PromptEnhancer** | Translates vague adjectives into precise visual instructions using cinematography vocabulary |

See `skills/core/cinematography-director.md` for the shot language reference.

</details>

<details>
<summary><strong>Music, Sound & Post-Production</strong></summary>

**Music & Sound:**

| Provider | Type | Notes |
| -------- | ---- | ----- |
| **Suno AI** | Cloud API | Full song generation with vocals, lyrics, any genre. Up to 8 minutes. |
| **ElevenLabs Music** | Cloud API | AI music generation |
| **ElevenLabs SFX** | Cloud API | Sound effect generation |
| **Pixabay Music** | Free Search | Royalty-free tracks, searchable by mood/BPM |

**Post-Production (always available, always free):**

| Tool | What It Does |
| ---- | ------------ |
| **FFmpeg** | Video composition, encoding, subtitle burn-in, audio muxing |
| **Video Stitch** | Multi-clip assembly, crossfades, picture-in-picture |
| **Video Trimmer** | Precision cutting and extraction |
| **Audio Mixer** | Multi-track mixing, ducking, fades |
| **Audio Enhance** | Noise reduction, normalization |
| **Color Grade** | LUT-based color grading |
| **Subtitle Gen** | SRT/VTT generation from timestamps |

**Composition & Rendering:**

| Engine | Type | What It Does |
| ------ | ---- | ------------ |
| **Remotion** | Local (Node.js) | React-based programmatic video — spring-animated image scenes, stat reveals, section titles, hero cards, TikTok-style word-by-word captions, scene transitions, Google Fonts, audio with fade curves |
| **HyperFrames** | Local (Node.js ≥ 22) | HTML/CSS/GSAP programmatic video — kinetic typography, product promos, launch reels, custom motion graphics, rigged SVG character animation |
| **FFmpeg** | Local | Core video assembly, encoding, subtitle burn, audio muxing, color grading |

</details>

---

## Style System

Style playbooks define the visual language for your productions:

| Playbook | Best For |
| -------- | -------- |
| **Clean Professional** | Corporate, educational, SaaS |
| **Flat Motion Graphics** | Social media, TikTok, startups |
| **Minimalist Diagram** | Technical deep-dives, architecture |

---

## Platform Output Profiles

Built-in render profiles for every major platform:

| Profile | Resolution | Aspect Ratio |
| ------- | ---------- | ------------ |
| YouTube Landscape | 1920×1080 | 16:9 |
| YouTube 4K | 3840×2160 | 16:9 |
| YouTube Shorts | 1080×1920 | 9:16 |
| Instagram Reels | 1080×1920 | 9:16 |
| Instagram Feed | 1080×1080 | 1:1 |
| TikTok | 1080×1920 | 9:16 |
| LinkedIn | 1920×1080 | 16:9 |
| Cinematic | 2560×1080 | 21:9 |

---

## Production Governance

### Quality Gates

- **Pre-compose validation** — blocks render if the delivery promise is violated, slideshow risk score is critical, or renderer family is missing
- **Post-render self-review** — after every render, runs ffprobe validation, extracts frames at 4 positions, analyzes audio levels, verifies the delivery promise
- **Slideshow risk scoring** — 6-dimension analysis prevents "animated PowerPoint" outputs
- **Source media inspection** — probes every supplied file before creative decisions are made

### Scored Provider Selection

Every tool selection runs through a 7-dimension scoring engine: task fit (30%), output quality (20%), control features (15%), reliability (15%), cost efficiency (10%), latency (5%), continuity (5%).

### Budget Controls

- **Estimate** before execution — see what it will cost
- **Configurable modes** — `observe` / `warn` / `cap`
- **Per-action approval** — pause for confirmation above a threshold (default: $0.50)
- **Total budget cap** — default $10, fully configurable

---

## Agent Compatibility

OpenMontage works with any AI coding assistant that can read files and execute Python.

| Platform | Config File |
| -------- | ----------- |
| **Claude Code** | `CLAUDE.md` |
| **Cursor** | `CURSOR.md` + `.cursor/rules/` |
| **GitHub Copilot** | `COPILOT.md` + `.github/copilot-instructions.md` |
| **Codex** | `CODEX.md` |
| **Windsurf** | `.windsurfrules` |

---

## Contributing

OpenMontage is built to be extended.

### Adding a New Tool

1. Create a Python file in the appropriate `tools/` subdirectory
2. Inherit from `BaseTool` and implement the tool contract
3. The registry auto-discovers it — no manual registration needed
4. Add a skill file if the tool needs usage guidance

### Adding a New Pipeline

1. Create a YAML manifest in `pipeline_defs/`
2. Create stage director skills in `skills/pipelines/<your-pipeline>/`
3. Reference existing tools — or add new ones if needed

See `docs/ARCHITECTURE.md` for the full technical reference and `AGENT_GUIDE.md` for the agent contract.

---

## Testing

```bash
# Linux / macOS
make test-contracts   # Run contract tests (no API keys needed)
make test             # Run all tests

# Windows
python -m pytest tests/contracts/
python -m pytest tests/
```

---

## License

[GNU AGPLv3](LICENSE)

---

## Contact

**Linhao**  
City University of Hong Kong (Dongguan)  
📧 [72510916@cityu-dg.edu.cn](mailto:72510916@cityu-dg.edu.cn)

---

**OpenMontage** — Production-grade AI video with professional cinematography planning, orchestrated by your AI assistant.
