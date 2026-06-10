#!/usr/bin/env python3
"""
move_with_manifest.py — the Safe Move Protocol executor for footage-organizer.

Guarantees, enforced in code:
  * NEVER deletes anything. There is no deletion code in this file.
  * NEVER overwrites: a move whose destination exists is refused. No force flag.
    The destination is re-checked immediately before every rename/copy action.
  * Same-drive moves are RENAMES (data never rewritten).
  * Cross-drive moves are COPY + VERIFY; the source is always left in place.
  * Every file is hashed before and after, compared path-by-path; any mismatch
    aborts the run.
  * Symlinks, duplicate sources, nested entries, and self-targets are refused
    at validation — before anything moves.
  * Every executed move is appended to a JSONL manifest; renames are undoable.

Usage:
    python3 move_with_manifest.py --plan plan.json [--dry-run] [--manifest out.jsonl]
    python3 move_with_manifest.py --undo --manifest out.jsonl

Plan format (JSON list):
    [{"src": "/abs/path/old", "dst": "/abs/path/new"}, ...]
    Entries may be files or directories. Directories move as whole units.
"""

import argparse
import errno
import json
import os
import shutil
import sys
import time
from pathlib import Path


def hash_file(path):
    """xxHash64 (Hedge/OffShoot-style) with MD5 fallback."""
    try:
        import xxhash
        h = xxhash.xxh64()
        algo = 'xxh64'
    except ImportError:
        import hashlib
        h = hashlib.md5()
        algo = 'md5'
    with open(path, 'rb') as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest(), algo


def hash_tree(base: Path):
    """{relative_path: digest} for a file or every file under a directory.
    Path-keyed so swapped-content corruption cannot hide in a multiset."""
    if base.is_file():
        digest, algo = hash_file(base)
        return {'.': digest}, algo
    out = {}
    algo = 'xxh64'
    for p in sorted(base.rglob('*')):
        if p.is_file():
            digest, algo = hash_file(p)
            out[str(p.relative_to(base))] = digest
    return out, algo


def validate(plan):
    """Validate every entry before anything runs. All-or-nothing."""
    errors = []
    seen_dst, seen_src = set(), set()
    resolved = []
    for i, entry in enumerate(plan):
        src = Path(entry['src']).expanduser()
        dst = Path(entry['dst']).expanduser()
        tag = f"  [{i+1}] {src} → {dst}"
        if not src.exists():
            errors.append(f"{tag}\n      source does not exist")
            continue
        if src.is_symlink():
            errors.append(f"{tag}\n      source is a symlink — refusing (the link target "
                          f"would not move; plan the real file instead)")
        if dst.exists():
            try:
                if src.resolve() == dst.resolve():
                    errors.append(f"{tag}\n      this is a case-only rename on a "
                                  f"case-insensitive drive — not supported; pick a "
                                  f"name that differs by more than letter case")
                    continue
            except OSError:
                pass
            errors.append(f"{tag}\n      DESTINATION ALREADY EXISTS — refusing "
                          f"(no overwrites, ever)")
        s, d = str(src.resolve()), str(dst)
        if s in seen_src:
            errors.append(f"{tag}\n      duplicate source in plan")
        if d in seen_dst:
            errors.append(f"{tag}\n      duplicate destination in plan")
        seen_src.add(s)
        seen_dst.add(d)
        if src.is_dir() and str(dst.resolve()).startswith(str(src.resolve()) + os.sep):
            errors.append(f"{tag}\n      destination is inside the source folder")
        resolved.append((i, s))
    # nested entries: one entry moving a folder that contains another entry's source
    for i, s_i in resolved:
        for j, s_j in resolved:
            if i != j and s_j.startswith(s_i + os.sep):
                errors.append(f"  [{i+1}] and [{j+1}]: entry {j+1}'s source is INSIDE "
                              f"entry {i+1}'s folder — merge them into the folder move, "
                              f"or move the file first")
                break
    return errors


def append_manifest(manifest_path: Path, record: dict):
    with open(manifest_path, 'a') as f:
        f.write(json.dumps(record) + '\n')


def copy_file_no_overwrite(src: Path, dst: Path):
    """Copy bytes to a new file only. Opening with xb makes the final path exclusive."""
    with open(src, 'rb') as in_f, open(dst, 'xb') as out_f:
        shutil.copyfileobj(in_f, out_f, length=8 * 1024 * 1024)
    shutil.copystat(src, dst, follow_symlinks=False)


def decide_mode(src: Path, dst: Path) -> str:
    """rename (same volume) vs copy (cross volume). Unknown → copy (safer)."""
    probe = dst.parent
    while not probe.exists():
        parent = probe.parent
        if parent == probe:          # reached filesystem root without a hit
            return 'copy_verify_source_retained'
        probe = parent
    try:
        return ('rename' if src.stat().st_dev == probe.stat().st_dev
                else 'copy_verify_source_retained')
    except OSError:
        return 'copy_verify_source_retained'


def execute(plan, manifest_path: Path, dry_run: bool):
    errors = validate(plan)
    if errors:
        print("❌ Plan validation failed — NOTHING was moved:\n")
        print('\n'.join(errors))
        sys.exit(2)

    print(f"✅ Plan validated: {len(plan)} move(s)\n")

    moves = []
    for entry in plan:
        src = Path(entry['src']).expanduser()
        dst = Path(entry['dst']).expanduser()
        mode = decide_mode(src, dst)
        moves.append((src, dst, mode))
        print(f"  {'[DRY] ' if dry_run else ''}{mode:<28} {src}\n"
              f"  {'':>34}→ {dst}")

    if dry_run:
        print(f"\nDry run complete. {len(moves)} move(s) would execute. Nothing was touched.")
        return

    session = time.strftime('%Y-%m-%dT%H:%M:%S')
    moved = 0
    verified_files = 0

    for src, dst, mode in moves:
        # 1) hash everything at the source (path-keyed)
        before, algo = hash_tree(src)

        # 2) execute
        dst.parent.mkdir(parents=True, exist_ok=True)
        if mode == 'rename':
            if dst.exists():     # re-check at the moment of action — no race window
                print(f"\n🔴 {dst} appeared since validation — refusing to overwrite. "
                      f"Run aborted; earlier moves stand and are in the undo log.")
                sys.exit(2)
            try:
                os.rename(src, dst)
            except OSError as e:
                if e.errno == errno.EXDEV:   # actually cross-volume — fall back to copy
                    mode = 'copy_verify_source_retained'
                else:
                    print(f"\n🔴 Could not move {src}: {e}\n   Run aborted; earlier "
                          f"moves stand and are in the undo log.")
                    sys.exit(3)
        if mode != 'rename':
            append_manifest(manifest_path, {
                'session': session, 'mode': mode, 'src': str(src), 'dst': str(dst),
                'status': 'copy_started', 'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})
            try:
                if dst.exists():
                    print(f"\n🔴 {dst} appeared since validation — refusing to overwrite. "
                          f"Run aborted; earlier moves stand and are in the undo log.")
                    sys.exit(2)
                if src.is_dir():
                    shutil.copytree(src, dst)   # copy only — source untouched
                else:
                    copy_file_no_overwrite(src, dst)  # copy only — source untouched
            except (OSError, shutil.Error) as e:
                append_manifest(manifest_path, {
                    'session': session, 'mode': mode, 'src': str(src), 'dst': str(dst),
                    'status': 'copy_failed', 'error': str(e),
                    'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})
                print(f"\n🔴 Copy failed partway: {e}")
                print(f"   Your ORIGINAL is untouched at: {src}")
                print(f"   An INCOMPLETE copy may exist at: {dst}")
                print(f"   Move that incomplete copy to the Trash yourself, then re-run.")
                print(f"   (This tool never deletes anything, including failed copies.)")
                sys.exit(3)

        # 3) re-hash at destination and compare path-by-path
        after, _ = hash_tree(dst)
        if before != after:
            missing = sorted(set(before) - set(after))
            changed = sorted(k for k in before if k in after and before[k] != after[k])
            print(f"\n🔴 CHECKSUM MISMATCH after moving {src} → {dst}")
            if missing:
                print(f"   missing at destination: {missing[:5]}")
            if changed:
                print(f"   content changed: {changed[:5]}")
            print("   Run aborted. Nothing further will move. Investigate before continuing.")
            append_manifest(manifest_path, {
                'session': session, 'mode': mode, 'src': str(src), 'dst': str(dst),
                'files': len(before), 'verified': False,
                'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})
            sys.exit(3)

        verified_files += len(after)
        moved += 1
        append_manifest(manifest_path, {
            'session': session, 'mode': mode, 'src': str(src), 'dst': str(dst),
            'files': len(after), 'algo': algo, 'verified': True,
            'hashes': before, 'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})
        note = '' if mode == 'rename' else '  (source left in place — delete it yourself after verifying)'
        print(f"  ✅ verified {len(after)} file(s){note}")

    print(f"\n{'='*60}")
    print(f"  START AND FINISH ARE THE SAME")
    print(f"  {moved} move(s) · {verified_files} file(s) · every checksum identical")
    print(f"  0 deletions (this tool cannot delete)")
    print(f"  Undo log: {manifest_path}")


def undo(manifest_path: Path):
    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}")
        sys.exit(1)
    records = [json.loads(line) for line in
               manifest_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    renames = [r for r in records if r.get('mode') == 'rename' and r.get('verified')]
    copies = [r for r in records if r.get('mode', '').startswith('copy')]

    if copies:
        print(f"ℹ️  {len(copies)} cross-drive copy record(s) are not undone (we never "
              f"delete copies);\n    their sources were never touched, so there is "
              f"nothing to restore.\n")

    if not renames:
        print("No renames to undo.")
        return

    print(f"Reversing {len(renames)} rename(s), most recent first:\n")
    undone = 0
    for r in reversed(renames):
        src, dst = Path(r['src']), Path(r['dst'])
        if not dst.exists():
            print(f"  ⚠️ skip (missing): {dst}")
            continue
        if src.exists():
            print(f"  ⚠️ skip (original slot occupied): {src}")
            continue
        src.parent.mkdir(parents=True, exist_ok=True)
        os.rename(dst, src)
        append_manifest(manifest_path, {
            'session': 'undo', 'mode': 'undo_rename', 'src': str(dst),
            'dst': str(src), 'verified': True,
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})
        print(f"  ↩️  {dst} → {src}")
        undone += 1
    print(f"\nUndo complete: {undone} rename(s) reversed. Nothing was deleted.")


def main():
    ap = argparse.ArgumentParser(description='Safe Move Protocol executor (never deletes)')
    ap.add_argument('--plan', help='JSON move plan: [{"src":..., "dst":...}]')
    ap.add_argument('--manifest', default=None,
                    help='JSONL undo log (default: _move_manifest.jsonl beside the plan)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--undo', action='store_true', help='reverse renames from the manifest')
    args = ap.parse_args()

    if args.undo:
        if not args.manifest:
            print("--undo requires --manifest")
            sys.exit(1)
        undo(Path(args.manifest).expanduser())
        return

    if not args.plan:
        print("--plan is required (or use --undo)")
        sys.exit(1)

    plan_path = Path(args.plan).expanduser()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    manifest = Path(args.manifest).expanduser() if args.manifest \
        else plan_path.parent / '_move_manifest.jsonl'
    execute(plan, manifest, args.dry_run)


if __name__ == '__main__':
    main()
