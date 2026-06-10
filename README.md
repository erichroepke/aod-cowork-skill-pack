# AOD Footage Pack

**Claude becomes your post supervisor.** Three skills for documentary filmmakers:

| Skill | What it does | What you say |
|-------|--------------|--------------|
| 🗂 **footage-organizer** | Audits your drive against a professional folder structure, then — with your approval — safely moves footage into place. Every move is verified with a digital fingerprint, everything is undoable, and deleting is impossible. | *"Check my footage folder"* · *"Organize this drive"* |
| 🔎 **footage-index** | A searchable memory of every drive you've ever scanned. Ask for a moment, get the drive, file, and timecode — even if that drive is on a shelf. | *"Where's the interview where she talks about her father?"* |
| 🎞 **footage-analyst** | Transcribes footage, identifies who's on screen (you label the faces), breaks down speakers, makes a beautiful HTML report. | *"Transcribe this clip"* · *"Who's in this video?"* |

Everything runs **on your computer**. No footage is ever uploaded anywhere.

---

## 🚨 Read this first

These skills work with camera originals — possibly the only copy of irreplaceable
material. They are built around one rule: **they cannot delete your files.** The
organizer only *moves* footage, only after you approve a plan, and only after you
confirm a backup exists. Before and after every move it checks each file's digital
fingerprint — the same kind of verification professional offload tools use — to prove
nothing changed in transit. If you ever change your mind, just say **"undo the
organizer's moves"** and Claude reverses everything automatically.

One important thing from us: **always keep a backup of your footage before organizing
— never work on the only copy.** The skill enforces this (it asks about your backup
before moving a single file), but you're the one responsible for protecting your
material. That's true of any tool that touches camera originals, this one included —
it's provided free, as-is.

---

## Install (first time, ~2 minutes)

You need the **Claude desktop app** (the one with Cowork). That's it — no other
software, and you will never need to open Terminal.

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

The skill takes it from there — it introduces itself, looks at your drive (reading
only — nothing moves without your approval), and talks you through everything. If a
skill ever needs a helper tool installed (like the transcription engine), **it asks
your permission and installs it for you**, narrating as it goes.

> 🧭 **Start with footage-organizer.** It needs nothing installed and gives you a
> full report of your drive in about a minute. Add the index next ("index this
> drive"). Install the analyst when you want transcripts and face ID — its one-time
> setup downloads about 4 GB of free AI tools that run privately on your Mac. It
> takes 10–20 minutes, Claude narrates progress the whole way (long quiet stretches
> are normal — it tells you which ones), and if anything gets interrupted it picks
> up exactly where it left off. You only ever do this once.

## Your first five minutes (just say these)

Everything in this pack is driven by talking to Claude. There's no app to learn —
these prompts are the product:

1. **"Check my footage folder"** → full audit report of your connected drive
2. **"Okay, organize it"** → Claude proposes a move plan, asks about your backup,
   and only acts when you approve
3. **"Index this drive — call it [your drive's name]"** → the drive becomes
   permanently searchable
4. **"Show me my footage library"** → a visual page of your clips, built from
   whatever you've indexed so far (so do step 3 first). Clips your browser can't
   preview show their location instead — Safari plays the most formats.
5. **"Transcribe this interview"** → transcript with timecodes (first run installs
   the free transcription engine — Claude walks you through it)
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
