# motion-lower-thirds

Generates branded, animated lower-third title templates for Apple Motion / Final Cut Pro
(built for the VAHC FOS 27 campaign).

It writes three templates into Motion's Titles folder (`Titles → VAHC` in Final Cut):

| Template | Look |
|---|---|
| FOS 27 lower third Pro | Navy plate with slanted end + sky tab, red council band |
| FOS 27 lower third Bar | Full-width navy band, red top stripe, red council tab |
| FOS 27 lower third Stacked | Navy name strip / white title strip / sky council strip |

Every template has:

- a **Logo drop zone**, published to FCP. Swap it in the Title Inspector or drag an image onto it.
  Images are fit (not cropped) into a square box.
- a fast staggered build-in/out (logo pops with overshoot, plates wipe from the left, text slides in)
- Build In / Build Out markers, so FCP only stretches the hold when you trim
- 4K / 59.94 fps, with brand colors navy `#002F6E`, sky `#2C8FE0`, red `#CC122E`

## How it works

Hand-built Motion XML is fragile, so the script starts from a working `.moti` (the original
"FOS 27 lower third" template) and reuses its text layers. It then:

1. removes the old behaviors, then restyles and re-keyframes the Name / Title / council text
2. converts the logo into a published drop zone
3. draws the plate graphics with Pillow and adds them as image layers, using per-frame keyframes for easing
4. adds markers and writes `large.png` / `small.png` thumbnails (a mockup, not a Motion render)

Each graphic PNG is twice its visible width and transparent on the left half. That puts the
layer's center on its left edge, so a scale-X wipe grows from the left without an anchor point.

## Usage

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python lowerthirds.py            # defaults use the FOS 27 files on this Mac
.venv/bin/python lowerthirds.py --help     # override base template, output dir, logo, font
```

Previews are written to `previews/`. **Close the templates in Motion before re-running.** The
script replaces the output folders, and saving a stale copy from Motion would undo the rebuild.

## Customizing

All layouts live in the `VARIANTS` list in `lowerthirds.py`:

- positions use Motion canvas coordinates (origin at center, +Y up, 3840×2160)
- `timing` is `(in start, in end, out start, out end)` in frames
- keep every out animation at or after `BUILD_OUT` (frame 246)
- the brand colors are constants at the top of the file
