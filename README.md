# AOD Footage Pack

**Claude becomes your post supervisor.** Three skills for documentary filmmakers:

| Skill | What it does | What you say |
|-------|--------------|--------------|
| 🗂 **footage-organizer** | Audits your drive against a professional folder structure, then — with your approval — safely moves footage into place. Every move is verified with a digital fingerprint, moves on the same drive are undoable with one command, and deleting is impossible. | *"Check my footage folder"* · *"Organize this drive"* |
| 🔎 **footage-index** | A searchable memory of every drive you've ever scanned. Ask for a moment, get the drive, file, and timecode — even if that drive is on a shelf. | *"Where's the interview where she talks about her father?"* |
| 🎞 **footage-analyst** | Transcribes footage, identifies who's on screen (you label the faces), breaks down speakers, makes a beautiful HTML report. | *"Transcribe this clip"* · *"Who's in this video?"* |

Treat them as one bundle, not three separate apps. **Organizer and analyst create the
evidence; index is the final "this folder is searchable now" step.** Once a folder is
indexed, you can just chat with Claude about the footage.

Everything runs **on your computer**. No footage is ever uploaded anywhere.

---

## 🚨 Read this first

These skills work with camera originals — possibly the only copy of irreplaceable
material. They are built around one rule: **they cannot delete your files.** The
organizer only *moves* footage, only after you approve a plan, and only after you
confirm a backup exists. Before and after every move it checks each file's digital
fingerprint — the same kind of verification professional offload tools use — to prove
nothing changed in transit. If you ever change your mind, just say **"undo the
organizer's moves"** and Claude reverses every move it made on that drive. (Moves
*between* drives work differently — and even more safely: the organizer copies and
verifies, and your original is never touched, so there is nothing to undo.)

One important thing from us: **always keep a backup of your footage before organizing
— never work on the only copy.** The skill enforces this (it asks about your backup
before moving a single file), but you're the one responsible for protecting your
material. That's true of any tool that touches camera originals, this one included —
it's provided free, as-is.

---

## Install (first time, ~2 minutes)

You need the **Claude desktop app** (the one with Cowork). For the organizer and the
index, that's it — no other software, and you will never need to open Terminal. The
analyst (transcription and face ID) needs free helper tools; **Claude installs those
for you** the first time you use it, asking permission as it goes — still no Terminal.

1. **Get the files.** Click the download link from your AOD course materials (or the
   **Releases** link on this page). Download the files that end in `.skill` — for
   example `footage-organizer.skill`. They land in your **Downloads** folder and show
   a Claude icon.
2. **Install each one.** With Claude open, **double-click the downloaded file**. A
   dialog should appear asking to add the skill — click **Install**. *(Nothing
   happened? Make sure Claude is open, then try again. Still nothing? Open Claude,
   click **Settings**, find **Skills** (sometimes under "Capabilities"), and drag the
   file from Downloads straight onto that window. Same result.)*
3. **Check it worked.** The skill appears in that Settings → Skills list. That's your
   confirmation.
4. **Use it.** Start a new Cowork conversation in Claude, give it access to your
   footage folder when it asks (or use the **+** / folder button in the chat to choose
   your project folder or drive), and type: **"check my footage folder"**

**Important:** do not drag individual video files into the chat. Put footage in the
project folder or connected drive first, then give Claude access to that folder. The
skills work by scanning the real folder on disk, preserving paths, drive names, card
structures, sidecars, and future index/search results.

The skill takes it from there — it introduces itself, looks at your drive (reading
only — nothing moves without your approval), and talks you through everything. If a
skill ever needs a helper tool installed (like the transcription engine), **it asks
your permission and installs it for you**, narrating as it goes.

> 🧭 **Install all three. Use them as one pack.** Start by asking Claude to run the
> AOD footage workflow on a folder or drive. Claude audits and safely organizes first,
> analyzes selected footage when transcripts or people are useful, then indexes last.
> After the index says the folder is complete, the normal interface is chat:
> "find the interview where..." or "show me everything with Sarah."

## How the bundle runs

The pack has one simple rhythm:

```
DOWNLOAD / CONNECT FOLDER
  -> ORGANIZE + VERIFY
  -> ANALYZE SELECTED FOOTAGE
  -> INDEX FINAL STATE
  -> CHAT WITH THE FOOTAGE
```

The steps can overlap, but the index is the durable finish line.

1. **Download / connect** — install all three `.skill` files, then give Claude access
   to the footage folder or drive. Do not attach media files to the chat; add them to
   the folder or drive and let Claude scan that location.
2. **Organize** — Claude scans the folder, shows the folder tree, flags issues, and
   proposes safe moves. Nothing moves until you approve and confirm a backup.
3. **Analyze** — Claude transcribes selected interviews or clips, labels people when
   needed, and creates local reports. This can run while the broader folder is being
   organized or checked.
4. **Index** — Claude ingests the final folder paths plus any transcripts and tags.
   The index is what lets you chat with the footage later.
5. **Chat** — ask normal questions. Claude searches the local index and answers with
   drive, file path, timecode, and matching quote when a transcript exists.

The status surface should stay plain: folder tree, checkmarks, counts, and a short
sidebar summary like **"This folder is indexed: 3 files, 1 transcript, 2 people/tags,
all moves verified."** The LLM reasoning stays in Claude; the visible UI only shows
media state and progress.

## Your first five minutes (just say these)

Everything in this pack is driven by talking to Claude. There's no app to learn —
these prompts are the product:

1. **"Run the AOD footage workflow on this folder"** → audit, summary, and next steps
2. **"Okay, organize it"** → Claude proposes a move plan, asks about your backup,
   and only acts when you approve
3. **"Transcribe these interviews"** → transcript with timecodes (first run installs
   the free transcription engine — Claude walks you through it)
4. **"Index this folder — call the drive [your drive's name]"** → the organized folder
   and analysis results become searchable
5. **"Show me my footage library"** → a simple indexed-folder summary plus visual
   previews where available
6. Months later: **"Which drive has the interview where she talks about her
   father?"** → drive name, file, timecode.

## Updating

Download the new `.skill` files from Releases and install them the same way — the new
version replaces the old one. **Then start a new chat** — Claude loads skills when a
session begins, so an update doesn't apply to chats that are already open.

---

## What's inside (for the curious)

```
footage-organizer/   SKILL.md + scan_tree.py, checksum_scan.py, move_with_manifest.py
footage-index/       SKILL.md + footage_index.py        (SQLite, all local)
footage-analyst/     SKILL.md + extract_faces.py, analyze_footage.py
build.sh             packages the .skill files (maintainers only)
```

- Organizer + index need **zero dependencies** — they run on what's already on a Mac.
- The analyst uses free, open-source AI (Whisper for transcription, local face
  clustering) — installed on demand, with your permission, all local.
- The index is one SQLite file at `~/Documents/FootageIndex/footage_index.db`.
  Delete that file and the index is gone (your footage is never touched).

## The folder framework

The organizer teaches a professional production structure — `00_projects` /
`01_footage` (shoots → dates → cameras → cards, originals preserved exactly) /
`02_music` / `03_archives` / `04_assets` / `05_proxies` / `09_exports`. The full spec
with rules lives in [footage-organizer/SKILL.md](footage-organizer/SKILL.md).

## License

MIT. Use freely, share freely. No warranty of any kind — **back up your footage.**

---

*Built for the Art of Documentary community. The pack finds and organizes your
material; for shaping the story it becomes, see [ARC](https://storyarc.co).*
