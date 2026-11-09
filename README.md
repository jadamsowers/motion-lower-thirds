# motion-lower-thirds

Generates branded, animated lower-third title templates for Apple Motion / Final Cut Pro.
Each brand (logo, colors, council line) lives in its own folder under `brands/`, so the same
three layouts can be built for any program or campaign.

For a brand named `NYLT`, it writes three templates into Motion's Titles folder:

| Template | Look |
|---|---|
| NYLT lower third Pro | Plate with slanted end + accent tab, council band |
| NYLT lower third Bar | Full-width plate band, top stripe, council tab |
| NYLT lower third Stacked | Plate name strip / white title strip / accent council strip |

Each also gets a **Vertical** copy (`NYLT lower third Pro Vertical`, …) on a 2160×3840 (9:16)
canvas for Shorts, Reels and TikTok. It's the same design, moved up and in so it clears the
captions and buttons those apps draw over the bottom ~880 px and right ~220 px. Use the vertical
copies in vertical projects and the regular ones in 16:9 projects.

Every template has:

- a **Logo drop zone**, published to FCP. Swap it in the Title Inspector or drag an image onto it.
  Images are fit (not cropped) into a square box.
- a fast staggered build-in/out (logo pops with overshoot, plates wipe from the left, text slides in)
- Build In / Build Out markers, so FCP only stretches the hold when you trim
- 4K / 59.94 fps

## Brands

| Folder | Templates | Final Cut category |
|---|---|---|
| `brands/nylt` | NYLT lower third … | Titles → NYLT |
| `brands/fos27` | FOS 27 lower third … (VAHC Friends of Scouting 2027) | Titles → VAHC |

Each brand folder holds a logo and a `brand.toml`:

```toml
name = "NYLT"                          # template names: "NYLT lower third Pro", ...
category = "NYLT"                      # Final Cut category (defaults to name)
council = "VIRGINIA HEADWATERS COUNCIL"
logo = "logo.jpg"                      # round logo on white or transparent

[colors]
plate = "#023876"       # plates and bars
plate_hi = "#0E4E96"    # top of the plate gradient (a little lighter than plate)
accent = "#005E9E"      # Pro tab, Stacked council strip
band = "#ED1848"        # council band, stripes
title_text = "#A9B8E0"  # Title line on the plate (keep it light)
```

**Adding a brand:** copy an existing folder (`cp -R brands/nylt brands/newthing`), drop in the
new logo, edit `brand.toml`, then build it. Use a round logo: the script cuts the logo into a
circle, sized from its widest point across the middle.

## Usage

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python lowerthirds.py nylt              # build one brand straight into Final Cut
.venv/bin/python lowerthirds.py nylt fos27        # several brands
.venv/bin/python lowerthirds.py all               # every brand in brands/
.venv/bin/python lowerthirds.py nylt --out templates   # build into the repo instead
.venv/bin/python lowerthirds.py --help
```

By default, templates go into `~/Movies/Motion Templates.localized/Titles.localized/<category>/`.
Restart Final Cut Pro afterwards so it picks them up. Previews are written to `previews/<brand>/`.

**Close the templates in Motion before re-running.** The script replaces the output folders, and
saving a stale copy from Motion would undo the rebuild.

## Prebuilt templates

Built copies are checked in under `templates/<category>/`. To install them without running the
script, copy the folder into Motion's Titles folder, then restart Final Cut Pro:

```sh
cp -R templates/NYLT ~/Movies/"Motion Templates.localized/Titles.localized/"
```

These copies are not updated automatically: rebuild with `--out templates` after a change.
`templates/VAHC/FOS 27 lower third/` is the original template every build starts from (the
`--base` default), so don't delete it.

## How it works

Hand-built Motion XML is fragile, so the script starts from a working `.moti` (the original
"FOS 27 lower third" template) and reuses its text layers. It then:

1. removes the old behaviors, then restyles and re-keyframes the Name / Title / council text
2. converts the logo into a published drop zone
3. draws the plate graphics with Pillow and adds them as image layers, using per-frame keyframes for easing
4. adds markers and writes `large.png` / `small.png` thumbnails (a mockup, not a Motion render)

Each graphic PNG is twice its visible width and transparent on the left half. That puts the
layer's center on its left edge, so a scale-X wipe grows from the left without an anchor point.

## Customizing layouts

The three layouts live in `variants()` in `lowerthirds.py`:

- positions use Motion canvas coordinates (origin at center, +Y up, 3840×2160)
- `timing` is `(in start, in end, out start, out end)` in frames
- keep every out animation at or after `BUILD_OUT` (frame 246)
- colors come from the brand's `brand.toml`
- `vertical()` derives the 9:16 copies: `V_DX` / `V_DY` shift each layout, `V_RIGHT` caps plate
  width, and full-width bars are narrowed to the vertical frame
