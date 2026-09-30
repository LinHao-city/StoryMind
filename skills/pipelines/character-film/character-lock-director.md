# Character Lock Director

This stage is a blocking gate. Real production waits until character references
exist and the user selects each canonical identity.

For every character, require explicit user approval, an existing master
identity file, an existing full-body file, and an existing locked reference
for every outfit required by the story. Keep identity separate from wardrobe.
The selected candidate ID must match the approved `character_candidates`
artifact. Use `character_media` to register derived views and outfits, then
record their project-local paths in `character_bible`.
Use `character_manager` to lock and validate each record. A beautiful image
with the wrong identity is never grounds to bypass the lock.

Complete the stage only with a `character_bible` whose cast is entirely locked
and whose story fingerprint matches the current locked story. Private source
permissions remain in force after character approval.
