# HyperFrames Skills — Provenance

The 12 HyperFrames-family skills under `.agents/skills/` are vendored from the upstream HyperFrames monorepo:

- **Source**: https://github.com/heygen-com/hyperframes
- **Vendored commit**: `3351fb1a` (`chore: release v0.7.17`, 2026-06-27)
- **Vendored tag**: `v0.7.17`
- **Vendor date**: 2026-06-27
- **Vendored by**: re-vendor on branch `chore/version-bumps-and-hf-resync`

## What's vendored

**Re-vendored from prior 0.4.2-era copies (renamed/restructured upstream):**

| Skill | Notes |
|---|---|
| `hyperframes` | Slim entry-point in 0.7; deep content moved to focused skills below. |
| `hyperframes-cli` | Greatly expanded in 0.7 (was 1 file, now 7). Now covers `validate`, `inspect`, `snapshot`, `benchmark`, `lambda`, etc. natively — the old OM-local patch teaching `validate` is obsolete and was dropped. |
| `hyperframes-registry` | Block/component registry workflow. |
| `website-to-video` | Renamed upstream from `website-to-hyperframes`. |

**Newly vendored (strategic additions in 0.5–0.7):**

| Skill | Why we want it in StoryMind |
|---|---|
| `hyperframes-core` | The composition contract — `data-*` timing, tracks, sub-compositions. The split-out core of what was in `hyperframes` 0.4. |
| `hyperframes-creative` | Non-animation creative direction — palette, type, narration, beat planning. |
| `hyperframes-media` | Audio + media assets — TTS, BGM, SFX, transcription, captions, background removal. |
| `hyperframes-animation` | All animation knowledge (rules, blueprints, transitions, techniques, 7 runtime adapters). Replaces ad-hoc motion guidance previously scattered in `hyperframes`. |
| `media-use` | Agent Media OS — one `resolve` verb resolves BGM/SFX/image/icon needs into local files via project/global cache + HeyGen catalog. Strategic for StoryMind asset stages. |
| `motion-graphics` | Short design-led motion graphic patterns (kinetic typography, stat reveals, logo stings, lower-thirds). |
| `remotion-to-hyperframes` | Migration guidance — directly relevant given StoryMind runs BOTH runtimes. |
| `music-to-video` | Beat-synced music-driven video workflow using `hyperframes beats`. |

## Intentionally NOT vendored

These upstream skills are HF-workflow-specific and would compete with or duplicate StoryMind's own pipeline routing. Re-evaluate per pipeline need:

`embedded-captions`, `faceless-explainer`, `general-video`, `pr-to-video`, `product-launch-video`, `slideshow`, `talking-head-recut`.

## Re-sync instructions

To re-vendor from a newer upstream:

```bash
cd C:/Users/ishan/Documents/hyperframes
git pull --ff-only origin main
# Then in StoryMind:
cd /c/Users/ishan/Documents/StoryMind
HF=C:/Users/ishan/Documents/hyperframes
for d in hyperframes hyperframes-cli hyperframes-registry hyperframes-core \
         hyperframes-creative hyperframes-media hyperframes-animation \
         media-use motion-graphics remotion-to-hyperframes \
         music-to-video website-to-video; do
  rm -rf ".agents/skills/$d"
  cp -r "$HF/skills/$d" ".agents/skills/$d"
done
# Then update vendor commit/tag/date at the top of this file.
```

## Future automation

Upstream 0.7 added `hyperframes skills` — a CLI that installs/updates HF skills with a freshness manifest and version check. Consider adopting it as the mechanical source of truth instead of hand-vendoring (would also auto-flag staleness across multi-agent setups). See `feat(cli): skills freshness — version check, manifest, global install + multi-agent mirror (#1753)` in HF history.
