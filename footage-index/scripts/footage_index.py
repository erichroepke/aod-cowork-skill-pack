#!/usr/bin/env python3
"""
footage_index.py — local, searchable memory of every footage drive.

SQLite + FTS5, zero dependencies (everything ships inside Python).
The index lives in ONE central database so it remembers drives that are
unplugged or on a shelf. Default: ~/Documents/FootageIndex/footage_index.db

READ-ONLY toward footage: this script only ever reads media folders.
It writes only to its own database file.

Subcommands:
    init                                          create/verify the database
    ingest-path  --path DIR --drive NAME          walk a folder, index media files
                 [--checksums _checksums.json]    attach hashes from checksum_scan.py
    ingest-transcript --file-path CLIP --json T [--drive NAME]
                                                  attach timecoded segments to a clip
    tag          --file-path CLIP [--drive NAME] --kind person|topic --value X
                 [--t-start S --t-end E]
    search       --terms "a,b,c" [--person X] [--topic Y] [--limit N]
    stats
    export-library --out library.json             full dump for the HTML library page

Transcript JSON format (what footage-analyst produces):
    [{"start": 12.4, "end": 19.1, "speaker": "SPEAKER_1", "text": "..."}, ...]
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

DEFAULT_DB = Path.home() / 'Documents' / 'FootageIndex' / 'footage_index.db'

MEDIA_EXTENSIONS = {
    '.mp4', '.mov', '.mxf', '.r3d', '.braw', '.ari', '.mts', '.m2ts',
    '.mpeg', '.mpg', '.m4v', '.mkv', '.webm', '.avi',
    '.wav', '.aiff', '.aif', '.bwf', '.flac', '.mp3', '.m4a',
}

WEB_PLAYABLE = {'.mp4', '.m4v', '.webm', '.mov', '.mp3', '.m4a', '.wav'}

ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

SCHEMA = """
CREATE TABLE IF NOT EXISTS drives (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    last_seen TEXT
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    drive_id INTEGER NOT NULL REFERENCES drives(id),
    path TEXT NOT NULL,
    name TEXT, ext TEXT, size INTEGER, mtime TEXT,
    shoot TEXT, shoot_date TEXT, camera TEXT, card TEXT,
    hash TEXT, web_playable INTEGER DEFAULT 0,
    UNIQUE(drive_id, path)
);
CREATE TABLE IF NOT EXISTS segments (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id),
    t_start REAL, t_end REAL, speaker TEXT, text TEXT
);
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id),
    t_start REAL, t_end REAL,
    kind TEXT NOT NULL,   -- 'person' | 'topic'
    value TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
    text, content=segments, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
    INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
    INSERT INTO segments_fts(segments_fts, rowid, text)
    VALUES('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS segments_au AFTER UPDATE ON segments BEGIN
    INSERT INTO segments_fts(segments_fts, rowid, text)
    VALUES('delete', old.id, old.text);
    INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


def connect(db_path):
    db_path = Path(db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    # Repair older databases that were created before delete/update triggers.
    con.execute("INSERT INTO segments_fts(segments_fts) VALUES('rebuild')")
    con.commit()
    return con


def parse_framework(rel_parts):
    """Infer shoot/date/camera/card from framework paths:
    01_footage/SHOOT/YYYY-MM-DD/CAM_X/CARD_YYY/...
    Returns (shoot, date, camera, card) — any may be None."""
    shoot = date = camera = card = None
    parts = list(rel_parts)
    if '01_footage' in parts:
        i = parts.index('01_footage')
        rest = parts[i + 1:]
        if rest and rest[0] != '00_INCOMING':
            # rest[-1] is the filename; shoot must be a folder component
            shoot = rest[0] if len(rest) > 1 else None
            if len(rest) > 2 and ISO_DATE.match(rest[1]):
                date = rest[1]
            for p in rest:
                if p.upper().startswith('CAM_'):
                    camera = p
                if p.upper().startswith('CARD_'):
                    card = p
    return shoot, date, camera, card


def tc(seconds):
    if seconds is None:
        return '--:--:--'
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def cmd_ingest_path(con, args):
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"ERROR: not a directory: {root}")
    drive = args.drive

    hashes = {}
    if args.checksums and Path(args.checksums).exists():
        data = json.loads(Path(args.checksums).read_text())
        for f in data.get('files', []):
            hashes[f.get('abs_path', '')] = f.get('computed')

    cur = con.cursor()
    cur.execute("INSERT INTO drives(name, last_seen) VALUES(?, ?) "
                "ON CONFLICT(name) DO UPDATE SET last_seen=excluded.last_seen",
                (drive, time.strftime('%Y-%m-%d %H:%M')))
    drive_id = cur.execute("SELECT id FROM drives WHERE name=?", (drive,)).fetchone()[0]

    added = updated = 0
    for fp in sorted(root.rglob('*')):
        if not fp.is_file() or fp.name.startswith('.'):
            continue
        if fp.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        rel = fp.relative_to(root)
        shoot, date, cam, card = parse_framework(rel.parts)
        st = fp.stat()
        row = (drive_id, str(rel), fp.name, fp.suffix.lower(), st.st_size,
               time.strftime('%Y-%m-%d', time.localtime(st.st_mtime)),
               shoot, date, cam, card, hashes.get(str(fp)),
               1 if fp.suffix.lower() in WEB_PLAYABLE else 0)
        existing = cur.execute("SELECT id FROM files WHERE drive_id=? AND path=?",
                               (drive_id, str(rel))).fetchone()
        if existing:
            cur.execute("""UPDATE files SET name=?,ext=?,size=?,mtime=?,shoot=?,
                        shoot_date=?,camera=?,card=?,hash=COALESCE(?,hash),web_playable=?
                        WHERE id=?""", row[2:] + (existing[0],))
            updated += 1
        else:
            cur.execute("INSERT INTO files(drive_id,path,name,ext,size,mtime,shoot,"
                        "shoot_date,camera,card,hash,web_playable) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        row)
            added += 1
    con.commit()
    print(f"✅ Drive '{drive}': {added} files added, {updated} updated.")


def find_file(con, file_path, drive=None):
    """Locate a file row by drive plus absolute path suffix or name."""
    name = Path(file_path).name
    params = [name]
    drive_filter = ''
    if drive:
        drive_filter = ' AND d.name=?'
        params.append(drive)
    rows = con.execute(
        "SELECT f.id, d.name, f.path FROM files f JOIN drives d ON d.id=f.drive_id "
        f"WHERE f.name=?{drive_filter}", params).fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        # disambiguate by how many trailing PATH COMPONENTS match (not raw
        # characters — "footage/A001.MOV" vs "backup-footage/A001.MOV" must
        # score differently against ".../footage/A001.MOV")
        want = Path(file_path).parts

        def suffix_score(row):
            have = Path(row[2]).parts
            n = 0
            for a, b in zip(reversed(want), reversed(have)):
                if a != b:
                    break
                n += 1
            return n

        rows.sort(key=suffix_score, reverse=True)
        if suffix_score(rows[0]) == suffix_score(rows[1]):
            print(f"⚠️  Ambiguous: '{name}' exists at the same relative path on "
                  f"multiple drives — using [{rows[0][1]}]. Pass --drive with "
                  f"the indexed drive name to target a different drive.")
    return rows[0][0]


def cmd_ingest_transcript(con, args):
    fid = find_file(con, args.file_path, args.drive)
    if fid is None:
        sys.exit(f"ERROR: file not in index (ingest its drive first): {args.file_path}")
    data = json.loads(Path(args.json).read_text(encoding='utf-8'))
    # Accept both a bare segment list (analyze_footage.py) and the
    # {"segments": [...]} object that whisper/mlx-whisper write.
    segs = data['segments'] if isinstance(data, dict) else data
    cur = con.cursor()
    cur.execute("DELETE FROM segments WHERE file_id=?", (fid,))  # replace, own-DB only
    for s in segs:
        cur.execute("INSERT INTO segments(file_id,t_start,t_end,speaker,text) "
                    "VALUES(?,?,?,?,?)",
                    (fid, s.get('start'), s.get('end'), s.get('speaker'),
                     (s.get('text') or '').strip()))
    con.commit()
    print(f"✅ {len(segs)} segments indexed for {Path(args.file_path).name}")


def cmd_tag(con, args):
    fid = find_file(con, args.file_path, args.drive)
    if fid is None:
        sys.exit(f"ERROR: file not in index: {args.file_path}")
    con.execute("INSERT INTO tags(file_id,t_start,t_end,kind,value) VALUES(?,?,?,?,?)",
                (fid, args.t_start, args.t_end, args.kind, args.value))
    con.commit()
    print(f"✅ tagged {Path(args.file_path).name}: {args.kind}={args.value}")


def cmd_search(con, args):
    terms = [t.strip() for t in (args.terms or '').split(',') if t.strip()]
    results = []

    if terms:
        # FTS5 phrase quoting; embedded double-quotes are escaped by doubling
        match = ' OR '.join('"{}"'.format(t.replace('"', '""')) for t in terms)
        q = """SELECT d.name, f.path, f.name, s.t_start, s.t_end, s.speaker,
                      snippet(segments_fts, 0, '>>', '<<', '…', 12), f.shoot, f.shoot_date
               FROM segments_fts
               JOIN segments s ON s.id = segments_fts.rowid
               JOIN files f ON f.id = s.file_id
               JOIN drives d ON d.id = f.drive_id
               WHERE segments_fts MATCH ? ORDER BY rank LIMIT ?"""
        for r in con.execute(q, (match, args.limit)):
            results.append(('transcript', r))

        # filename + tag matches
        for t in terms:
            like = f'%{t}%'
            for r in con.execute(
                    """SELECT d.name, f.path, f.name, NULL, NULL, NULL,
                              'filename match', f.shoot, f.shoot_date
                       FROM files f JOIN drives d ON d.id=f.drive_id
                       WHERE f.name LIKE ? OR f.shoot LIKE ? LIMIT ?""",
                    (like, like, args.limit)):
                results.append(('file', r))
            for r in con.execute(
                    """SELECT d.name, f.path, f.name, t.t_start, t.t_end, t.kind || ': ' || t.value,
                              'tag match', f.shoot, f.shoot_date
                       FROM tags t JOIN files f ON f.id=t.file_id
                       JOIN drives d ON d.id=f.drive_id
                       WHERE t.value LIKE ? LIMIT ?""", (like, args.limit)):
                results.append(('tag', r))

    if args.person:
        for r in con.execute(
                """SELECT d.name, f.path, f.name, t.t_start, t.t_end, t.value,
                          'person', f.shoot, f.shoot_date
                   FROM tags t JOIN files f ON f.id=t.file_id
                   JOIN drives d ON d.id=f.drive_id
                   WHERE t.kind='person' AND t.value LIKE ? LIMIT ?""",
                (f'%{args.person}%', args.limit)):
            results.append(('person', r))

    if args.topic:
        for r in con.execute(
                """SELECT d.name, f.path, f.name, t.t_start, t.t_end, t.value,
                          'topic', f.shoot, f.shoot_date
                   FROM tags t JOIN files f ON f.id=t.file_id
                   JOIN drives d ON d.id=f.drive_id
                   WHERE t.kind='topic' AND t.value LIKE ? LIMIT ?""",
                (f'%{args.topic}%', args.limit)):
            results.append(('topic', r))

    if not results:
        print("No matches. Try broader terms — or this footage may not be transcribed yet "
              "(file-level search works without transcripts; content search needs them).")
        return

    seen = set()
    print(f"\n🔎 {len(results)} match(es):\n")
    for kind, r in results[:args.limit]:
        drive, path, name, t0, t1, who, hit, shoot, date = r
        key = (drive, path, t0)
        if key in seen:
            continue
        seen.add(key)
        loc = f"[{drive}] {path}"
        when = f"  @ {tc(t0)}–{tc(t1)}" if t0 is not None else ''
        ctx_bits = [b for b in (shoot, date) if b]
        ctx = f"  ({' '.join(ctx_bits)})" if ctx_bits else ''
        print(f"  • {name}{when}{ctx}\n    {loc}\n    {who or ''} {hit}\n")


def cmd_stats(con, args):
    f = con.execute("SELECT COUNT(*), COALESCE(SUM(size),0) FROM files").fetchone()
    s = con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
    t = con.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    print(f"\n📚 Footage Index")
    for did, name, last in con.execute("SELECT id, name, last_seen FROM drives ORDER BY name"):
        n = con.execute("SELECT COUNT(*) FROM files WHERE drive_id=?", (did,)).fetchone()[0]
        tr = con.execute("SELECT COUNT(DISTINCT file_id) FROM segments s "
                         "JOIN files f ON f.id=s.file_id WHERE f.drive_id=?", (did,)).fetchone()[0]
        print(f"   💾 {name}: {n} files · {tr} transcribed (last seen {last})")
        for shoot, cnt in con.execute(
                "SELECT COALESCE(shoot,'(no shoot folder)'), COUNT(*) FROM files "
                "WHERE drive_id=? GROUP BY shoot ORDER BY shoot", (did,)):
            print(f"      🎬 {shoot}: {cnt} file(s)")
    transcribed = con.execute("SELECT COUNT(DISTINCT file_id) FROM segments").fetchone()[0]
    tagged = con.execute("SELECT COUNT(DISTINCT file_id) FROM tags WHERE kind='person'").fetchone()[0]
    pct = (100 * transcribed // f[0]) if f[0] else 0
    print(f"\n   TOTALS: {f[0]} files · {f[1] / 1024**3:.1f} GB · {s} transcript segments · {t} tags")
    print(f"   🔎 Content search covers {transcribed}/{f[0]} files ({pct}%) — "
          f"the rest are findable by name/shoot only")
    print(f"   👤 {tagged} file(s) have people tagged")
    if f[0] and transcribed < f[0]:
        print(f"   💡 To make more footage searchable by what's said: run footage-analyst "
              f"on the untranscribed clips\n")
    else:
        print()


def cmd_export_library(con, args):
    out = {'generated': time.strftime('%Y-%m-%d %H:%M'), 'drives': {}, 'files': []}
    for fid, drive, path, name, ext, size, shoot, date, cam, card, playable in con.execute(
            """SELECT f.id, d.name, f.path, f.name, f.ext, f.size, f.shoot,
                      f.shoot_date, f.camera, f.card, f.web_playable
               FROM files f JOIN drives d ON d.id=f.drive_id"""):
        segs = [{'start': a, 'end': b, 'speaker': c, 'text': d2} for a, b, c, d2 in
                con.execute("SELECT t_start,t_end,speaker,text FROM segments "
                            "WHERE file_id=? ORDER BY t_start", (fid,))]
        tags = [{'kind': k, 'value': v, 'start': a} for k, v, a in
                con.execute("SELECT kind,value,t_start FROM tags WHERE file_id=?", (fid,))]
        out['files'].append({'drive': drive, 'path': path, 'name': name, 'ext': ext,
                             'size': size, 'shoot': shoot, 'date': date, 'camera': cam,
                             'card': card, 'web_playable': bool(playable),
                             'segments': segs, 'tags': tags})
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"✅ library JSON → {args.out} ({len(out['files'])} files)")


def main():
    ap = argparse.ArgumentParser(description='Local footage index (SQLite FTS5)')
    ap.add_argument('--db', default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('init')
    p = sub.add_parser('ingest-path')
    p.add_argument('--path', required=True)
    p.add_argument('--drive', required=True, help='drive/volume label, e.g. LACIE_4TB')
    p.add_argument('--checksums', default=None)
    p = sub.add_parser('ingest-transcript')
    p.add_argument('--file-path', required=True)
    p.add_argument('--json', required=True)
    p.add_argument('--drive', default=None, help='indexed drive name when clip paths repeat')
    p = sub.add_parser('tag')
    p.add_argument('--file-path', required=True)
    p.add_argument('--drive', default=None, help='indexed drive name when clip paths repeat')
    p.add_argument('--kind', required=True, choices=['person', 'topic'])
    p.add_argument('--value', required=True)
    p.add_argument('--t-start', type=float, default=None)
    p.add_argument('--t-end', type=float, default=None)
    p = sub.add_parser('search')
    p.add_argument('--terms', default='', help='comma-separated, pre-expanded by Claude')
    p.add_argument('--person', default=None)
    p.add_argument('--topic', default=None)
    p.add_argument('--limit', type=int, default=20)
    sub.add_parser('stats')
    p = sub.add_parser('export-library')
    p.add_argument('--out', required=True)

    args = ap.parse_args()
    con = connect(args.db)
    {'init': lambda c, a: print(f"✅ index ready: {args.db}"),
     'ingest-path': cmd_ingest_path,
     'ingest-transcript': cmd_ingest_transcript,
     'tag': cmd_tag,
     'search': cmd_search,
     'stats': cmd_stats,
     'export-library': cmd_export_library}[args.cmd](con, args)


if __name__ == '__main__':
    main()
