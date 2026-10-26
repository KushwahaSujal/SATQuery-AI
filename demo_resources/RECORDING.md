# Recording the SIH demo video

A vertical (1080×1920) YouTube Short. Two horizontal screen recordings are cut into vertical shots, hard
cut to hard cut:

| # | Deliverable | Input | Prompt |
|---|---|---|---|
| Setup | Backend + frontend started from the terminal | — | `start_backend.sh`, `start_frontend.sh` |
| 1 | Text-prompted masking | `recording/inputs/1_masking_airport.png` | `mask airplanes` |
| 2 | Visual question answering (same image, follow-up box) | — | `what type of area is shown in this image?` |
| 3 | Bi-temporal change detection | `recording/inputs/2_change_t1_before.png` + `2_change_t2_after.png` | `detect building changes` |
| 4 | Video object search | `recording/inputs/3_video_aerial.mp4` | `find all vehicles` |
| 5 | GeoTIFF: water extent in km² | `recording/inputs/4_geotiff_valencia_sentinel2.tif` | `segment the water bodies` |
| 6 | Optical + SAR: routes, then refuses honestly | `recording/inputs/5_optical_sentinel2.png` + `5_sar_sentinel1_cband.png` | `analyze this optical and SAR pair` |

Everything in this file was run on the **deployed** stack on 2026-09-23 (Vercel + Modal T4, warm
container). Numbers below are what that run returned.

---

## 1. The day before

1. **Ship today's two fixes once, off camera.** They are in the working tree, not yet deployed:
   the result page now opens on the mask / change overlay (not the plain RGB image), and the backend's
   "SAM 2.1" layer no longer serves the bare input. Run the same two scripts you will run on camera:
   ```bash
   scripts/demo/start_backend.sh      # modal deploy, warm GPU
   scripts/demo/start_frontend.sh     # vercel deploy --prod
   ```
   Then do one masking prompt on https://satquery-ai-smoky.vercel.app and check the result opens on
   **Grounding Evidence Overlay** with green planes. Then `scripts/demo/stop_backend.sh`.
   The on-camera run is then an identical, cached re-deploy (Modal ≈ 5 s, Vercel ≈ 40 s).
2. **ffmpeg** for the edit: `sudo apt install ffmpeg` (or `pip install imageio-ffmpeg` in any venv).
3. **Screen:** 1920×1080 display, browser **full-screen (F11)**, zoom **100%**, dark theme. The crop
   boxes in `edit_plan.example.json` assume exactly this. Terminal font **≥ 22 pt** — it gets shrunk ~50%.
4. **Recorder** (OBS/SimpleScreenRecorder/GNOME `Ctrl+Alt+Shift+R`): 1920×1080, 30 fps, MKV. Mute
   desktop audio; record voice separately or add it in the editor.
5. Turn off notifications. Close other tabs.

## 2. Fifteen minutes before

```bash
scripts/demo/start_backend.sh                           # if not already warm
.venv/bin/python scripts/demo/rehearse_deployed.py      # wakes every model the demo uses
```
All four rows must say `COMPLETED`. This also puts the demo prompts at the top of the sidebar history,
which looks fine; if you want a clean sidebar, delete old jobs from **History** first.

## 3. Take 1 — terminal (`raw/01_terminal.mkv`)

From the repo root, full-screen terminal:
```bash
scripts/demo/start_backend.sh
scripts/demo/start_frontend.sh
```
Each prints the real command in cyan before running it. Stop when you see
`Frontend live at https://satquery-ai-smoky.vercel.app`.

> The site you open next is the one `vercel deploy` just published, and it talks to the Modal backend
> `modal deploy` just started — never to your laptop. Say it that way; it is accurate.
> (`start_*.sh local` runs both on this machine instead, if you ever need an offline demo.)

## 4. Take 2 — the website (`raw/02_site.mkv`), one continuous take

Open https://satquery-ai-smoky.vercel.app, pause 2 s on the home page (**AI Ready · 18/20**), then
**New Analysis**.

| Step | Do | Wait (measured) | What appears |
|---|---|---|---|
| 1 Masking | **Attach** → `1_masking_airport.png`, type `mask airplanes`, Enter | ~40 s | Opens on **Grounding Evidence Overlay**: all six planes green. Hover the Detected Regions list. |
| 2 VQA | In **Ask another question about this same image…** type `what type of area is shown in this image?`, Enter | ~25 s | New job page, workflow `workflow_single_vqa`: *"This image shows an airport tarmac with several small aircraft…"* |
| 3 Change | **New Analysis** → **Attach** → select **both** `2_change_t1_before.png` and `2_change_t2_after.png`, type `detect building changes`, Enter | ~60 s | Opens on **ChangeFormer — Temporal Change Overlay**: new buildings in red. *"118,998 pixels changed (11.35%)"*, 181 regions. |
| 4 Video | **New Analysis** → **Attach** → `3_video_aerial.mp4`, type `find all vehicles`, Enter | ~2 min | 2 events on the timeline (14.9–18.7 s, 25.4–27.4 s). Click the first event card → video jumps there with the red car boxed, `vehicles · 0.84`. |

| 5 GeoTIFF | **New Analysis** → **Attach** → `4_geotiff_valencia_sentinel2.tif`, type `segment the water bodies`, Enter | ~40 s | Real Sentinel-2B scene (Albufera lagoon, Valencia; 10 m/px, EPSG:32630). Opens on the overlay: lagoon + sea green, land untouched. *"61.06% … (160,055 px, 16.01 km²) … 10 m/px from its georeferencing, matching the 10 m/px it was trained and validated at"*, 96% confidence; side panel **Estimated area 16.01 km²**. |
| 6 Optical + SAR | **New Analysis** → **Attach** → select **both** `5_optical_sentinel2.png` and `5_sar_sentinel1_cband.png`, type `analyze this optical and SAR pair`, Enter | ~10–25 s | Workflow card: **workflow_optical_sar** — *"Dual cross-modal Optical + SAR images provided for sensor fusion."* Answer + Warnings: fusion model **NOT_CONFIGURED**, no output produced. Click the SAR layer in the list to show the radar image. |

Hold still ~3 s on every finished result — those seconds become the "result" shots.

## 5. What to say, and what not to

One line per shot is plenty; the captions carry the rest.

- **Masking:** "Type what you want in plain English. Grounding DINO proposes the airplanes, SAM 2.1
  segments each one, and a verification agent checks the top match."
- **VQA:** "Ask a follow-up on the same image — the router sends it to the visual question-answering
  workflow."
- **Change:** "Two dates of the same area. ChangeFormer, trained on LEVIR-CD, marks new buildings —
  about 11% of this scene."
- **GeoTIFF:** "A real Sentinel-2 GeoTIFF. The system reads its georeferencing — 10 metres per pixel —
  so the water segmenter, trained on Sentinel-2 at that resolution, reports area in square kilometres:
  about 16 km² of water."
- **Optical + SAR:** "Give it an optical and a radar image and the router recognises a cross-sensor
  pair. Our fusion head isn't trained yet, so instead of inventing land-cover numbers the system says
  so. Zero fabrication is a design rule."
- **Video:** "Upload aerial video and ask for vehicles. It samples frames, detects, segments,
  verifies, and returns time-stamped events."

Avoid, because the screen contradicts it:
- **Don't read out "9 instances"** in the masking answer. There are six planes; some are split into two
  masks. *Key Findings* shows **Regions detected: 6** — point at that if you want a number.
- **Don't say "every vehicle"** in the video. The parked white car is not boxed; say "finds the moments a
  vehicle appears".
- **Optical + SAR:** never call it "fusion results". It routes correctly and then refuses — present
  the refusal as the feature (`docs/OPTICAL_SAR_FUSION_ENABLEMENT.md`). Its layer list labels the two
  images "Earlier (T1)" / "Later (T2)"; they are two sensors, not two dates — don't read that out.
- **GeoTIFF footer** says "Models: grounding_dino, sam2"; the trained water segmenter did the work (the
  answer names it). Don't read the footer.
- Any before/after pair now works, in any selection order and from the follow-up box: the backend
  puts the pair in time order from the filenames (before/after, pre/post, t1/t2, old/new, dates) —
  Q-061. Before that fix, the browser sent "after" first and the same scene measured 5.06% instead of
  11.35%.
- The masking answer's *Key Findings* says "Changed pixels: 13,795" — a label reused from change
  detection. Harmless; don't draw attention to it.

## 6. Editing into the vertical Short

```bash
cd demo_resources/recording
cp edit_plan.example.json edit_plan.json        # then edit in/out times to your takes
mkdir -p raw                                    # put 01_terminal.mkv and 02_site.mkv here
python ../../scripts/demo/make_vertical.py --grab raw/02_site.mkv 1:00   # check a crop box
python ../../scripts/demo/make_vertical.py edit_plan.json --preview      # fast 540×960 check
python ../../scripts/demo/make_vertical.py edit_plan.json                # final 1080×1920
python ../../scripts/demo/make_vertical.py edit_plan.json --only 7       # redo one shot, rejoin
```
Use `.venv/bin/python` if your system Python lacks Pillow.

Each shot: blurred fill of the recording behind, the cropped region(s) stacked in the middle, the
deliverable name on top, a caption below, and an automatic **"8× speed"** badge on every sped-up wait.
The script prints the runtime and warns above 3:00 (the example plan is 2:06). Add voiceover or music
in any editor afterwards — segments at normal speed keep their audio, sped-up ones are silent.

## 7. After recording

```bash
scripts/demo/stop_backend.sh     # scale the GPU back to zero — a warm T4 bills around the clock
```
