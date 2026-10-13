# Banana runbook

Resume notes for the "fill this repo with banana images" chat. Keep this under 1,500 tokens and update it as work happens.

## Goal
Fill `aaron1612n-cmd/banana` with as many banana images as possible. Only public-domain or CC-licensed images, each credited in `CREDITS.csv`. Branch: `claude/determined-brown-wvyrco`. It is the repo's only branch, so no PR can be opened. Commit and push as you go.

## Current state (2026-10-13)
- 24,345 images in 202 folders under `images/<topic>/`, about 4.0 GB. Everything is pushed and the tree is clean.
- Sources:
  - Openverse searches: English, 30 other-language words for banana, and food/plant terms.
  - Wikimedia Commons, partial.
  - iNaturalist: 10,405 research-grade photos of the banana genus Musa, resized to 800px, in `musa-*` species folders.
- Files are named after their titles (slugified). Camera-code titles fall back to `<topic>-N`. Folders hold at most 900 files, because GitHub truncates listings at 1,000.

## Decisions made
- Free licenses only; the user chose this over "anything".
- Existing file names never change. `organize.py` keeps already-organized paths and only names new files.
- NSFW content is deleted outright (user request). The old `images/nsfw/` folder is gone.
- Non-banana images are removed with CLIP ViT-B/16 zero-shot scoring (`classify.py`), skipping iNaturalist:
  - title mentions banana in any language: remove if score < 0.25
  - no banana word in the title: remove if score < 0.6
  - The cutoffs were set by hand-checking sample grids. 3,811 images were removed.
- NSFW pass (`nsfw.py`): removed 91 photos from Ecuador's "World Banana Queen" pageant (creator "Alcaldía de Joseph Cueva") plus 3 other images. The top 330 hits were checked by eye.
- New batches get the same CLIP filters before merging.
- Ambiguous queries were dropped: "banana slug", "platano" (unaccented, Italian for plane tree), "muz". For other-language queries, results are kept only if the title names a banana.

## Open items / ideas
- Wikimedia is throttling this container's IP (HTTP 429): about 1,700 queued images and a category crawl stuck around "Category:Red banana". Only retry from a fresh IP or session.
- Deleted images are still in git history, so a clone is over 5 GB. Purging needs a history rewrite and force push, and the user hasn't approved that.
- The repo is near GitHub's soft 5 GB limit, so resize new batches (`RESIZE=800`).
- Other possible sources: more Openverse queries (20 requests/min, ~200/day anonymous), GBIF, Smithsonian Open Access. The Met API returned 410.

## How to resume
1. Unpack the state into a scratch folder S: `tar -xzf tools/state/state.tar.gz -C $S`, then `cp tools/scripts/*.py $S/scripts/`.
   - The archive holds `all.dl.json` (download status and repo path for every item), the per-source manifests, and the CLIP score files.
2. Collect: `collect*.py` (Openverse, resumable, with a 429 backoff loop), `inat.py`, `commons.py`.
3. Download into staging, not the repo:
   - `RESIZE=800 ONLY=other python3 -I download.py <state>.json stage <manifest>`
   - `ONLY=wikimedia` downloads one image at a time with 960px thumbnails.
4. Filter staging with `classify.py` and `nsfw.py`. They need a venv with CPU torch (`--index-url https://download.pytorch.org/whl/cpu`) and `transformers`.
5. Merge into the repo:
   - Move kept files into `images/`, add their entries to `all.dl.json`, then run `organize.py all.dl.json /home/user/banana <all manifests>`.
   - That rewrites `CREDITS.csv`. Update the README folder count.
6. Commit and push in batches of 700 MB or less (pushes over 2 GB fail).
7. Check new images visually with `sheets.py` (numbered contact sheets) before committing.

## Gotchas
- `pkill -f <pattern>` matches the calling shell. Kill by PID instead.
- Background waits are capped at 2 hours. Use `nohup` for long jobs and poll.
- A container restart kills background jobs. `classify.py` resumes from its score file.
- The stop hook complains about untracked files, so keep staging outside the repo.
