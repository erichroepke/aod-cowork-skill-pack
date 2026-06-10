# Changelog

## 2.0.1 — 2026-06-10

Four-agent review pass (beginner experience, code correctness, adversarial safety,
consistency). Fixes:

- **move_with_manifest.py hardened:** path-keyed before/after hash comparison
  (catches swapped-content corruption), symlink/duplicate-source/nested-entry
  rejection at validation, destination re-checked at the moment of every rename
  (no race window), EXDEV fallback to copy, unknown-volume cases default to the
  safer copy mode, failed cross-drive copies leave a manifest record and
  plain-English recovery steps, case-only renames get a clear explanation
- **checksum_scan.py:** sidecars of a different algorithm now report 🟠
  "unverifiable" instead of false corruption alarms or silent replacement;
  empty-folder scan no longer crashes
- **footage_index.py:** accepts whisper/mlx-whisper `{"segments": [...]}` JSON
  directly; same-name clips on multiple drives disambiguate by path components
  (with a warning when truly ambiguous); FTS5 quote escaping; `--topic` filter
  actually works
- **analyst scripts:** refuse `--output` inside `01_footage/` or any card folder
- **SKILL.mds:** folder renames classified as moves (no freehand `mv` loophole),
  backup-gate trust doesn't relax checksums, plain-English narration rules
  (no scary flags shown to users), HuggingFace explained in human terms,
  `.xxh64` naming unified
- **README:** rewritten install steps with checkpoints and fallbacks, warmer
  safety section, undo explained, install-time expectations set
- **Added LICENSE** (MIT — was declared but missing)

## 2.0.0 — 2026-06-10

The pack release. Two skills become three, and the organizer learns to act.

### footage-organizer 2.0.0
- **Spine flip:** from read-only auditor to safe mover. New Safe Move Protocol:
  scan → propose plan → backup gate → approval → checksum before → move (rename;
  cross-drive is copy+verify, source retained) → checksum after → undo log
- Still cannot delete. Now enforced in code, not just instructions
  (`move_with_manifest.py` contains no deletion calls; destinations that exist are
  refused — no overwrites, no force flag)
- New `scan_tree.py`: summarizing scanner — multi-TB drives no longer flood the chat
- New eval: move-protocol behavior (backup gate, plan-first, never-delete)

### footage-index 1.0.0 (new)
- One local SQLite database remembers every drive scanned: files, shoots, cameras,
  cards, hashes, transcript segments, person/topic tags
- FTS5 search with Claude-side semantic query expansion; results return drive +
  path + timecode
- `export-library` feeds a generated HTML footage library (browse, filter, search,
  in-browser playback for web-playable clips)

### footage-analyst 2.0.0
- Pre-flight checks (disk/RAM/chip) + honest time expectations before installing
- Resume-safe, checkpointed installer messaging
- **Quick-transcribe fast path:** mlx-whisper on Apple Silicon (no 2 GB PyTorch
  download) for transcription-only requests
- Phase 2 `transcript.json` + face labels now feed the footage index

### Pack
- `build.sh`: .skill packages are built from one canonical source (kills version
  drift and 0-byte packages), with zip integrity verification
- Beginner-first README (install via Releases, double-click/drag, no terminal)

## 1.0.0 — 2026-06-10 (morning session)
- footage-organizer (read-only audit + xxHash64) and footage-analyst (two-phase
  face/transcript pipeline), first packaged versions
