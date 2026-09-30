# Character Discovery Director

Read the completed, locked `story_bible`. Identify each character's role,
age category, visual importance, dialogue needs, required outfits, and whether
user photos will be used. Use `character_manager` to make draft records, then
assemble `character_bible` with `story_fingerprint(story_bible)`.

For private family photos, keep `source_photos_local_only: true`,
`remote_character_creation_allowed: false`, and
`downstream_use_original_photos: false` by default. Explain that an
agent-native image call with a source photo is remote processing; obtain an
explicit change to the permission before Phase 2 does so.

Do not generate character candidates or movie shots in this stage. Present
the cast and outfit requirements for user review before checkpoint completion.
