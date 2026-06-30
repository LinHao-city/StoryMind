# Cinematography Director — Shot Language Reference

## When To Use

Read this skill **before** generating any video prompt. It is the single source of
truth for cinematography vocabulary in StoryMind. Never describe shots with vague
adjectives ("epic", "cinematic", "dramatic") without translating them into their
visual causes first.

---

## The Shot Planning Workflow (Mandatory)

Every production request goes through three steps before video generation:

```
1. StoryboardPlanner  → decompose script into structured shots (JSON)
2. CharacterSheet     → register characters; inject descriptions into prompts
3. SceneConsistencyTracker → register style anchors; append to all prompts
```

Only after these three tools run should `leihuo_video` or any video generator be called.

---

## Shot Scale Vocabulary

| Code | Full Name | Use When |
|------|-----------|----------|
| ECU | Extreme Close-Up | Extreme emotion, single detail (eye, hand, object) |
| CU | Close-Up | Reaction, intimacy, face reading |
| MCU | Medium Close-Up | Dialogue, relationship beats |
| MS | Medium Shot | Interaction, physical action |
| MLS | Medium Long Shot | Character in motion |
| LS | Long Shot | Character placed in full environment |
| WS | Wide Shot | Character + significant surroundings |
| EWS | Extreme Wide Shot | Scale, isolation, establishing |
| Aerial | Bird's Eye / Drone | God-view, consequence, transition |

**Rule**: No two consecutive shots should use the same scale. Rhythm = variation.

---

## Camera Movement Vocabulary

| Movement | Visual Effect | Use For |
|----------|--------------|---------|
| static | Stability, observation | Tension, formality, meditation |
| dolly-in | Intensification | Revelation, intimacy, threat |
| dolly-out / pull-back | Isolation | Consequence, scale reveal |
| pan left/right | Spatial reveal | Following action, landscape |
| tilt-up | Power, ascension | Awe, authority, hope |
| tilt-down | Vulnerability, gravity | Defeat, descent |
| tracking shot | Urgency | Chase, following character |
| crane-up | God's view | Climax, departure, fate |
| handheld | Chaos, urgency | Combat, panic, documentary |
| arc shot | Environment reveal | Introduce space, character |

**Critical distinction**: "zoom" (lens compression) ≠ "dolly" (camera movement).
Use dolly-in/out. Reserve optical zoom for deliberate unease/voyeurism only.

---

## Lighting Vocabulary

| Term | Visual Quality | Use For |
|------|---------------|---------|
| high-key | Bright, open, flat | Optimism, commercial, exposition |
| low-key | Dark, high contrast | Drama, danger, mystery |
| practical-lighting | Motivated sources visible | Intimacy, realism |
| motivated-window | Natural light from window | Hope, normalcy, transition |
| golden-hour | Warm, 5000K, long shadows | Nostalgia, beauty, endings |
| cold-blue | 7000K, clinical | Sci-fi, alienation, sadness |
| neon-accent | Saturated colored sources | Cyberpunk, modernity |
| backlit-silhouette | Subject in front of light | Mystery, power, iconic |
| rim-lighting | Edge light separates subject | Cinematic depth, prestige |
| anamorphic-flare | Horizontal lens flare | Prestige cinema, scale |

---

## Emotional Beat → Visual Translation Table

| Story Beat | Shot Recipe |
|-----------|-------------|
| Revelation / discovery | ECU on face → dolly-out to show context |
| Threat approaching | Low-angle WS → quick cut to MCU |
| Isolation / loneliness | EWS static, subject tiny in frame |
| Determination / resolve | CU low-angle, static, rim-lit |
| Wonder / awe | Tilt-up or crane-up, cold-blue → warm transition |
| Farewell / ending | Slow pull-back, golden-hour or cold-blue fade |
| Time passing | Match-cut between similar compositions |
| Deception | Over-the-shoulder MCU, slightly off-axis |

---

## The 5-Aspect Prompt Checklist (CHAI Method)

Before submitting any prompt to a video generator, verify all 5 aspects:

1. **Subject** — Who/what is the focus? Described precisely (not just "a scientist").
2. **Subject Motion** — What are they doing? Camera movement specified?
3. **Scene** — Where? Time of day? Weather? Lighting source?
4. **Spatial Framing** — Shot scale specified? (ECU/CU/MS/WS/EWS/Aerial)
5. **Camera** — Movement specified? (static/dolly/pan/crane/handheld)

If any aspect is missing: fill it in. If intentionally omitted (e.g., no subject for a scenery shot), note it explicitly.

**Checklist template**:
```
Subject:         [exact description with character anchor if applicable]
Subject motion:  [action]
Scene:           [location, time, weather, light source]
Framing:         [shot scale code]
Camera:          [movement]
Full prompt:     [assembled]
```

---

## Consistency Rules Across a Sequence

1. **Register the style of Shot 1** using `SceneConsistencyTracker` → all subsequent shots inherit it
2. **Character descriptions must be verbatim** — copy exact wording from `CharacterSheet`, never paraphrase
3. **Color temperature is sacred** — if Shot 1 is cold-blue, every shot is cold-blue unless a deliberate warm shift marks a story turning point
4. **Aspect ratio** — choose once (16:9 cinematic or 2.35:1 anamorphic), never mix
5. **Grain/texture** — specify once ("cinematic grain", "clean digital", "film grain 35mm"); propagate

---

## Shot Sequencing Principles (from Jellyfish)

A well-structured sequence follows this arc:

```
Shot 1: EWS establishing  →  context, scale, mood
Shot 2: WS or LS          →  character in space
Shot 3: MS                →  action / interaction begins
Shot 4: CU                →  emotional reaction / detail
Shot 5: ECU / Insert      →  maximum tension / revelation
Shot 6: WS or EWS         →  resolution / consequence
```

Transitions:
- **Hard cut**: same energy level, fast pacing
- **Match cut**: visual rhyme between compositions (powerful)
- **Dissolve**: time passing, memory, dream
- **Fade to black/white**: finality, new chapter

---

## Phase 3 Preview: InstantID Face Locking

When GPU is available, add this to the workflow **after** video generation:

```python
from tools.enhancement.instantid_facelock import InstantIDFaceLock

# Lock protagonist face across all generated clips
locker = InstantIDFaceLock()
locker.execute({
    "reference_image": "projects/my_film/character_refs/protagonist.jpg",
    "video_paths": ["scene1.mp4", "scene2.mp4", "scene3.mp4"],
    "output_dir": "projects/my_film/render/face_locked/",
    "strength": 0.8,
})
```

Requires: NVIDIA GPU ≥ 16GB VRAM, `pip install -r requirements-gpu.txt`
