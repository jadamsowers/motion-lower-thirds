"""Build a branded lower-third family from the original FOS 27 .moti.

Every variant: drop-zone logo (published as "Logo" so it can be swapped in FCP),
snappy keyframed build in/out, Build In/Out markers, thumbnails.

Usage: python lowerthirds.py BRAND [BRAND ...] [--out DIR] [--base X.moti] [--font TTF]
Each brand is a folder in brands/ with a brand.toml and its logo; see README.
"""
import argparse
import copy
import re
import shutil
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HOME = Path.home()
REPO = Path(__file__).parent
BRANDS = sorted(p.parent.name for p in (REPO / "brands").glob("*/brand.toml"))
ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("brands", nargs="+", metavar="BRAND", choices=BRANDS + ["all"],
                help=f"brand folder(s) in brands/, or all ({', '.join(BRANDS)})")
ap.add_argument("--out", default=str(HOME / "Movies/Motion Templates.localized/Titles.localized"),
                help="Motion Titles folder; each brand goes in its category subfolder")
ap.add_argument("--base", default=str(REPO / "templates/VAHC/FOS 27 lower third/FOS 27 lower third.moti"),
                help="original .moti whose text layers are reused")
ap.add_argument("--font", default="/System/Library/PrivateFrameworks/Slideshows.framework/Versions/A/Resources/Content/Fonts/Proxima Nova Bold.ttf",
                help="font used only for drawing thumbnails")
ARGS = ap.parse_args()
SRC, OUT_ROOT, FONT = ARGS.base, Path(ARGS.out), ARGS.font
PREVIEWS = REPO / "previews"

# ---------------- brand ----------------
WHITE = (255, 255, 255)
COLOR_KEYS = ("plate", "plate_hi", "accent", "band", "title_text")


def load_brand(bid):
    d = REPO / "brands" / bid
    b = tomllib.loads((d / "brand.toml").read_text(encoding="utf-8"))
    b["id"], b["logo"] = bid, d / b["logo"]
    b.setdefault("category", b["name"])
    missing = set(COLOR_KEYS) - set(b["colors"])
    assert not missing, f"{bid}: brand.toml is missing colors {sorted(missing)}"
    b["colors"] = {k: tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for k, v in b["colors"].items()}
    return b


FPS_UNITS = 2002  # one frame at 59.94 in a 120000 timescale
END = 300
BUILD_IN, POSTER, BUILD_OUT = 40, 120, 246
SS = 4  # supersampling for graphics

LOGO_ID, LOGO_CLIP = 1825766578, 1825766577
NAME_ID, TITLE_ID, COUNCIL_ID = 1998666244, 1998666699, 1998667460


def t(f):
    return f"{int(round(f * FPS_UNITS))} 120000 1 0"


# ---------------- easing / keyframes ----------------
def out_expo(x):
    return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def in_cubic(x):
    return x ** 3


def out_back(x, c1=1.9):
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def curve(default, segs, minmax=None):
    pts = {}
    for f0, f1, v0, v1, ease in segs:
        for f in range(f0, f1 + 1):
            pts[f] = v0 + (v1 - v0) * ease((f - f0) / (f1 - f0))
    k = sorted(pts.items())
    out = [f'<curve type="1" default="{default}" value="{k[-1][1]:.6g}">',
           f"\t<numberOfKeypoints>{len(k)}</numberOfKeypoints>"]
    if minmax:
        out += [f"\t<min>{minmax[0]}</min>", f"\t<max>{minmax[1]}</max>"]
    for f, v in k:
        out.append(f'\t<keypoint interpolation="1" flags="0"><time>{t(f)}</time><value>{v:.6g}</value></keypoint>')
    out.append("</curve>")
    return "\n".join(out)


def anim(name, pid, default, segs, minmax=None):
    return f'<parameter name="{name}" id="{pid}" flags="8589934608">\n{curve(default, segs, minmax)}\n</parameter>'


def static(name, pid, default, value):
    return f'<parameter name="{name}" id="{pid}" flags="8589934608" default="{default}" value="{value}"/>'


def blending(segs):
    return ('<parameter name="Blending" id="200" flags="8589938704">\n'
            + anim("Opacity", 202, 1, segs, (0, 1)) + "\n</parameter>\n")


def fade(i0, i1, o0, o1):
    return [(i0, i1, 0, 1, out_cubic), (o0, o1, 1, 0, in_cubic)]


# ---------------- graphics ----------------
def shape_png(path, w, h, fill, alpha=255, slant=0, gradient=None, tab=None, left_accent=None):
    """Draw content w x h into the RIGHT half of a 2w-wide canvas, so the image
    center is the content's left edge and a scale-X wipe grows from the left."""
    im = Image.new("RGBA", (2 * w * SS, h * SS), (0, 0, 0, 0))
    x0, H = w * SS, h * SS
    right = x0 + (w - (tab[0] + tab[1] if tab else 0)) * SS
    poly = [(x0, 0), (right, 0), (right - slant * SS, H), (x0, H)]
    fill_img = Image.new("RGBA", im.size)
    fd = ImageDraw.Draw(fill_img)
    for y in range(H):
        c = fill
        if gradient:
            u = y / H
            c = tuple(int(gradient[i] * (1 - u) + fill[i] * u) for i in range(3))
        fd.line([(0, y), (im.size[0], y)], fill=c + (alpha,))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    im.paste(fill_img, (0, 0), mask)
    d = ImageDraw.Draw(im)
    if tab:  # (gap, width, color) stripe after the slanted edge
        gap, tw, col = tab
        tx = right + gap * SS
        d.polygon([(tx, 0), (tx + tw * SS, 0), (tx + tw * SS - slant * SS, H), (tx - slant * SS, H)], fill=col + (255,))
    if left_accent:  # (width, color) vertical bar at the left edge
        aw, col = left_accent
        d.rectangle([x0, 0, x0 + aw * SS, H], fill=col + (255,))
    im.resize((2 * w, h), Image.LANCZOS).save(path)


def square_logo(logo, dst):
    """Default drop-zone image: the round logo cut out on a transparent square."""
    src = Image.open(logo).convert("RGBA")
    flat = Image.new("RGBA", src.size, WHITE + (255,))
    flat.alpha_composite(src)
    src = flat.convert("RGB")
    px = src.load()
    W, H = src.size
    cy = H // 2
    row = [x for x in range(W) if sum(px[x, cy]) < 700]          # non-white pixels across the middle
    cx = W // 2
    col = [y for y in range(H) if sum(px[cx, y]) < 700]
    l, r, tp, b = row[0], row[-1], col[0], col[-1]
    size = max(r - l, b - tp) + 4
    box = (l + (r - l) // 2 - size // 2, tp + (b - tp) // 2 - size // 2)
    crop = src.crop((box[0], box[1], box[0] + size, box[1] + size)).convert("RGBA")
    m = Image.new("L", (size * SS, size * SS), 0)
    ImageDraw.Draw(m).ellipse((2 * SS, 2 * SS, (size - 2) * SS, (size - 2) * SS), fill=255)
    crop.putalpha(m.resize((size, size), Image.LANCZOS))
    crop.resize((1000, 1000), Image.LANCZOS).save(dst)


def media_name(g):
    """Media file for a graphic. Keep these names stable: FCP caches templates while
    it's running, and a renamed file makes that layer silently disappear."""
    return g.get("file") or re.sub(r"\W+", "_", g["name"].lower()) + ".png"


# ---------------- XML helpers ----------------
def node_span(s, node_id):
    m = re.search(rf'<scenenode name="[^"]*" id="{node_id}" factoryID="\d+" version="5">', s)
    return m.start(), s.index("</scenenode>", m.start()) + len("</scenenode>")


def edit_node(s, node_id, fn):
    a, b = node_span(s, node_id)
    return s[:a] + fn(s[a:b]) + s[b:]


def full_timing(blk):
    return re.sub(r'<timing in="[^"]*" out="[^"]*" offset="[^"]*"/>',
                  f'<timing in="0 1 1 0" out="{t(END)}" offset="0 1 1 0"/>', blk)


def text_editor(x, spec):
    font, size, y, rgb, (i0, i1), (o0, o1), text = spec

    def fn(blk):
        blk = re.sub(r"<font>[^<]*</font>", f"<font>{font}</font>", blk)
        blk = re.sub(r'(<parameter name="Size" id="3" flags="\d+" default="48" value=")[^"]*"', rf'\g<1>{size}"', blk)
        blk = full_timing(blk)
        xpos = anim("X", 1, 0, [(i0, i1, x - 70, x, out_cubic), (o0, o1, x, x - 50, in_cubic)])
        blk = re.sub(r'<parameter name="X" id="1" flags="8589934608" default="0" value="[^"]*"/>', lambda m: xpos, blk, count=1)
        blk = re.sub(r'(<parameter name="Y" id="2" flags="8589934608" default="0" value=")[^"]*"', rf'\g<1>{y}"', blk, count=1)
        blk = blk.replace('<parameter name="Lighting" id="230"',
                          blending(fade(i0, i1 - 6, o0, o1)) + '<parameter name="Lighting" id="230"', 1)
        color = ('<parameter name="Color" id="16" flags="8589938704">\n<foldFlags>15</foldFlags>\n'
                 + "".join(static(c, i + 1, 1, f"{v / 255:.6f}") + "\n" for i, (c, v) in enumerate(zip(("Red", "Green", "Blue"), rgb)))
                 + "</parameter>\n")
        face = '<parameter name="Face" id="14" flags="8589938704">\n\t\t\t\t\t\t<foldFlags>131072</foldFlags>'
        assert face in blk
        blk = blk.replace(face, face + "\n" + color, 1)
        if text:
            blk = re.sub(r"<text>[^<]*</text>", f"<text>{text}</text>", blk)
        return blk
    return fn


def logo_editor(pos, scale):
    def fn(blk):
        blk = full_timing(blk)
        blk = blk.replace('value="-1525.8517723082068"', f'value="{pos[0]}"').replace('value="-683.34899902254381"', f'value="{pos[1]}"')
        sc = [(0, 20, 0.001, scale, out_back), (264, 280, scale, 0.001, in_cubic)]
        scale_xml = ('<parameter name="Scale" id="105" flags="8589938704">\n<foldFlags>15</foldFlags>\n'
                     + anim("X", 1, 1, sc) + "\n" + anim("Y", 2, 1, sc) + "\n</parameter>")
        blk = re.sub(r'<parameter name="Scale" id="105".*?</parameter>', lambda m: scale_xml, blk, count=1, flags=re.S)
        blk = re.sub(r'<parameter name="Blending" id="200".*?</curve>\s*</parameter>\s*</parameter>\n',
                     lambda m: blending(fade(0, 6, 274, 280)), blk, count=1, flags=re.S)
        # drop zone: replaceable media, fit inside a 1000x1000 box
        blk = blk.replace('<parameter name="Source Media" id="300" flags="81604444176"',
                          '<parameter name="Source Media" id="300" flags="12901744656"')
        obj = re.search(r'<parameter name="Object" id="2" flags="8589938704">.*?</parameter>', blk, re.S)
        blk = blk[:obj.start()] + '''<parameter name="Object" id="2" flags="8589938704">
				<parameter name="Drop Zone" id="311" flags="8589934738" default="0" value="1"/>
				<parameter name="Fit" id="317" flags="8606777360" default="0" value="0"/>
				<parameter name="Use Display Aspect Ratio" id="323" flags="8606711824" default="0" value="0"/>
				<parameter name="Fit Factor" id="318" flags="8589938706">
					<parameter name="X" id="1" flags="8589934608" default="1" value="1"/>
					<parameter name="Y" id="2" flags="8589934608" default="1" value="1"/>
				</parameter>
				<parameter name="Width" id="313" flags="8589934610" default="1" value="1000"/>
				<parameter name="Height" id="314" flags="8589934610" default="1" value="1000"/>
			</parameter>''' + blk[obj.end():]
        return blk
    return fn


def image_node(name, nid, clip_id, w, h, pos, wipe, op):
    scale = ('<parameter name="Scale" id="105" flags="8589938704">\n<foldFlags>15</foldFlags>\n'
             + anim("X", 1, 1, wipe) + "\n</parameter>\n")
    return f'''		<scenenode name="{name}" id="{nid}" factoryID="12" version="5">
<validTracks>1</validTracks>
<aspectRatio>0</aspectRatio>
<flags>0</flags>
<timing in="0 1 1 0" out="{t(END)}" offset="0 1 1 0"/>
<foldFlags>16384</foldFlags>
<baseFlags>524368</baseFlags>
<parameter name="Properties" id="1" flags="8589938704">
<parameter name="Transform" id="100" flags="8589938704">
<parameter name="Position" id="101" flags="8589938704">
<foldFlags>15</foldFlags>
{static("X", 1, 0, pos[0])}
{static("Y", 2, 0, pos[1])}
</parameter>
{scale}</parameter>
{blending(op)}<parameter name="Color" id="243" flags="8589938690">
<parameter name="Hidden Channel" id="245" flags="8589934610" default="1" value="3"/>
<parameter name="Conversion Type" id="247" flags="8590032912" default="3" value="3"/>
<parameter name="PQ Peak (nits)" id="248" flags="8589967376" default="1000" value="1000"/>
</parameter>
<parameter name="Media" id="324" flags="8589938704">
<foldFlags>4</foldFlags>
<parameter name="Source Media" id="300" flags="81604444176" default="{clip_id}" value="{clip_id}"/>
<parameter name="Source Media" id="325" flags="8590000146"/>
</parameter>
<parameter name="Page Number" id="301" flags="8589934610" default="1" value="1"/>
<parameter name="Retime Value" id="304" flags="8590066066" default="1" value="1"/>
<parameter name="Retime Value Cache" id="319" flags="8590065810" default="1" value="1"/>
</parameter>
<parameter name="Object" id="2" flags="8589938704">
<parameter name="Width" id="313" flags="8589934610" default="1" value="{w}"/>
<parameter name="Height" id="314" flags="8589934610" default="1" value="{h}"/>
</parameter>
</scenenode>
'''


def clip(name, cid, rel, w, h):
    return f'''<clip name="{name}" id="{cid}">
<relativeURL>{rel}</relativeURL>
<missingWidth>{w}</missingWidth>
<missingHeight>{h}</missingHeight>
<missingDuration>0.033333333333333333</missingDuration>
<missingDynamicRangeType>0</missingDynamicRangeType>
<creationDuration>1</creationDuration>
<mediaID></mediaID>
<flags>0</flags>
<timing in="0 1 1 0" out="0 120000 1 0" offset="0 1 1 0"/>
<foldFlags>0</foldFlags>
<baseFlags>524304</baseFlags>
<parameter name="Properties" id="1" flags="8589938704"/>
<parameter name="Object" id="2" flags="8589938704">
<parameter name="Alpha Type" id="100" flags="8589938706">
<parameter name="Alpha Type" id="101" flags="8590000130" default="0" value="1"/>
</parameter>
<parameter name="Frame Rate" id="107" flags="8589934594" default="0" value="59.939999999999998"/>
<parameter name="Missing Is Still" id="128" flags="8589934610" default="0" value="1"/>
<parameter name="Footage Version" id="131" flags="8589934610" default="1" value="2"/>
</parameter>
</clip>
'''


# ---------------- variants ----------------
# graphics: front-to-back. pos = (left edge x, center y). wipe/op = (in f0, in f1, out f0, out f1)
def variants(b):
    c, council = b["colors"], b["council"]
    return [
        dict(
            title=f"{b['name']} lower third Pro",
            logo=((-1330, -664), 0.44),
            text_x=-1050,
            text={
                NAME_ID: ("ProximaNova-Bold", 150, -620, WHITE, (14, 34), (250, 262), None),
                TITLE_ID: ("ProximaNova-Medium", 80, -735, c["title_text"], (18, 38), (252, 264), None),
                COUNCIL_ID: ("ProximaNova-Semibold", 44, -840, WHITE, (22, 40), (248, 260), council),
            },
            graphics=[
                dict(name="Red Band", file="band.png", w=1340, h=68, pos=(-1330, -824), timing=(10, 32, 260, 274),
                     draw=dict(fill=c["band"], slant=20)),
                dict(name="Plate", w=1720, h=320, pos=(-1330, -630), timing=(6, 30, 264, 278),
                     draw=dict(fill=c["plate"], gradient=c["plate_hi"], alpha=245, slant=90, tab=(22, 26, c["accent"]))),
            ],
        ),
        dict(
            title=f"{b['name']} lower third Bar",
            logo=((-1330, -665), 0.40),
            text_x=-1060,
            text={
                NAME_ID: ("ProximaNova-Bold", 130, -715, WHITE, (14, 34), (250, 262), None),
                TITLE_ID: ("ProximaNova-Medium", 72, -810, c["title_text"], (18, 38), (252, 264), None),
                COUNCIL_ID: ("ProximaNova-Semibold", 38, -572, WHITE, (24, 40), (248, 258), council),
            },
            graphics=[
                dict(name="Council Tab", w=820, h=62, pos=(-1080, -559), timing=(16, 34, 256, 268),
                     draw=dict(fill=c["band"], slant=22)),
                dict(name="Red Stripe", w=3840, h=10, pos=(-1920, -595), timing=(4, 26, 262, 276),
                     draw=dict(fill=c["band"])),
                dict(name="Bar", w=3840, h=250, pos=(-1920, -725), timing=(6, 30, 264, 278),
                     draw=dict(fill=c["plate"], gradient=c["plate_hi"], alpha=240)),
            ],
        ),
        dict(
            title=f"{b['name']} lower third Stacked",
            logo=((-1330, -658), 0.40),
            text_x=-1060,
            text={
                NAME_ID: ("ProximaNova-Bold", 140, -620, WHITE, (14, 34), (250, 262), None),
                TITLE_ID: ("ProximaNova-Semibold", 72, -748, c["plate"], (20, 38), (252, 264), None),
                COUNCIL_ID: ("ProximaNova-Semibold", 38, -822, WHITE, (24, 40), (248, 260), council),
            },
            graphics=[
                dict(name="Accent Strip", w=900, h=56, pos=(-1150, -808), timing=(14, 34, 256, 270),
                     draw=dict(fill=c["accent"])),
                dict(name="White Plate", w=1180, h=110, pos=(-1150, -725), timing=(10, 32, 260, 274),
                     draw=dict(fill=WHITE, alpha=245)),
                dict(name="Navy Plate", w=1560, h=190, pos=(-1150, -575), timing=(6, 30, 264, 278),
                     draw=dict(fill=c["plate"], gradient=c["plate_hi"], alpha=245, tab=(0, 18, c["band"]))),
            ],
        ),
    ]


# ---------------- vertical (9:16) ----------------
# A vertical copy of each layout for Shorts/Reels/TikTok: same design on a 2160x3840 canvas,
# kept clear of the button column those apps draw down the right ~220 px, and sitting
# ~580 px (15%) above the bottom edge.
V_SIZE = (2160, 3840)
V_DX, V_DY = 570, -456  # logo ~100 px from the left edge, graphic bottom ~580 px up
V_RIGHT = 860           # plates stop here, clear of the right-hand button column


def vertical(v):
    v = copy.deepcopy(v)
    v["title"] += " Vertical"
    v["size"] = V_SIZE
    v["preview_crop"] = (0, 2144 - V_DY, 2160, 3044 - V_DY)
    (lx, ly), sc = v["logo"]
    v["logo"] = ((lx + V_DX, ly + V_DY), sc)
    v["text_x"] += V_DX
    v["text"] = {k: (font, size, y + V_DY, *rest) for k, (font, size, y, *rest) in v["text"].items()}
    for g in v["graphics"]:
        x, y = g["pos"]
        if g["w"] == 3840:  # full-width bar stays full width
            x, g["w"] = -V_SIZE[0] // 2, V_SIZE[0]
        else:
            x += V_DX
            g["w"] = min(g["w"], V_RIGHT - x)
        g["pos"] = (x, y + V_DY)
    return v


def set_canvas(s, w, h):
    s = s.replace("<width>3840</width>\n\t\t<height>2160</height>", f"<width>{w}</width>\n\t\t<height>{h}</height>", 1)
    for name, pid, val in (("Fixed Width", 302, w), ("Fixed Height", 303, h), ("Aperture Width", 312, w), ("Aperture Height", 313, h)):
        s, n = re.subn(rf'(<parameter name="{name}" id="{pid}" flags="\d+" default=")\d+(" value=")\d+"', rf'\g<1>{val}\g<2>{val}"', s)
        assert n == 2, (name, n)  # text group + layer
    assert f"<width>{w}</width>" in s
    return s


def build(v, base_xml, logo_png, out_dir, previews):
    d = out_dir / v["title"]
    if d.exists():
        shutil.rmtree(d)
    (d / "Media").mkdir(parents=True)
    shutil.copy(logo_png, d / "Media" / "logo.png")

    s = set_canvas(base_xml, *v.get("size", (3840, 2160)))
    s = re.sub(r"\n\t*<behavior name=\"[^\"]*\" id=\"\d+\" factoryID=\"\d+\">.*?</behavior>", "", s, flags=re.S)
    for nid, spec in v["text"].items():
        s = edit_node(s, nid, text_editor(v["text_x"], spec))
    # text group: start at 0, no offset
    s = s.replace('<timing in="18018 120000 1 0" out="558558 120000 1 0" offset="0 1 1 0"/>\n\t\t\t<foldFlags>0</foldFlags>\n\t\t\t<baseFlags>524368</baseFlags>',
                  f'<timing in="0 1 1 0" out="{t(END)}" offset="0 1 1 0"/>\n\t\t\t<foldFlags>0</foldFlags>\n\t\t\t<baseFlags>524368</baseFlags>', 1)
    s = s.replace('value="-512.92933959910135"', 'value="0"').replace('value="-682.84902191041192"', 'value="0"')

    pos, scale = v["logo"]
    s = edit_node(s, LOGO_ID, logo_editor(pos, scale))
    s = re.sub(r"<relativeURL>Media/FOS%2027%20round%20logo.svg</relativeURL>", "<relativeURL>Media/logo.png</relativeURL>", s)
    s = s.replace('<clip name="FOS 27 round logo" id="1825766577">', '<clip name="Logo" id="1825766577">')
    s = s.replace('<scenenode name="FOS 27 round logo" id="1825766578"', '<scenenode name="Logo" id="1825766578"')
    s = re.sub(r'(<clip name="Logo" id="1825766577">.*?)<missingWidth>1920</missingWidth>\s*<missingHeight>1080</missingHeight>',
               r"\1<missingWidth>1000</missingWidth>\n\t\t\t<missingHeight>1000</missingHeight>", s, count=1, flags=re.S)

    s = re.sub(r'(<clip name="Logo" id="1825766577">.*?)<parameter name="Fixed Width" id="114" flags="12884901888" default="1920" value="1920"/>\s*<parameter name="Fixed Height" id="115" flags="12884901888" default="1080" value="1080"/>',
               r'\1<parameter name="Fixed Width" id="114" flags="12884901888" default="1000" value="1000"/>\n<parameter name="Fixed Height" id="115" flags="12884901888" default="1000" value="1000"/>', s, count=1, flags=re.S)
    assert 'default="1000" value="1000"/>' in s

    # graphics behind text; Motion stacks the first XML child frontmost
    nodes, clips = "", ""
    for i, g in enumerate(v["graphics"]):
        fn = media_name(g)
        shape_png(d / "Media" / fn, g["w"], g["h"], **g["draw"])
        nid, cid = 1999100001 + i, 1999100101 + i
        i0, i1, o0, o1 = g["timing"]
        nodes += image_node(g["name"], nid, cid, 2 * g["w"], g["h"], g["pos"],
                            [(i0, i1, 0.001, 1, out_expo), (o0, o1, 1, 0.001, in_cubic)],
                            fade(i0, i0 + 2, o1 - 2, o1))
        clips += clip(g["name"], cid, f"Media/{fn}", 2 * g["w"], g["h"])
    a, b = node_span(s, LOGO_ID)
    logo_xml = s[a:b]
    s = s[:a] + nodes.lstrip("\t") + s[b:]
    anchor = '\t\t<group name="Group" id="1998667929">'
    s = s.replace(anchor, "\t\t" + logo_xml + "\n" + anchor, 1)
    s = s.replace('\t<footage name="Media Layer" id="10006">\n', '\t<footage name="Media Layer" id="10006">\n' + clips, 1)

    # publish the logo well + markers
    s = s.replace("\t<publishSettings>\n\t\t<version>2</version>\n\t</publishSettings>",
                  f'\t<publishSettings>\n\t\t<version>2</version>\n\t\t<target object="{LOGO_ID}" channel="./1/324/300" name="Logo"/>\n\t</publishSettings>', 1)
    mk = "".join(f"\n\t\t<timemarker>\n\t\t\t<inpoint>{t(f)}</inpoint>\n\t\t\t<color>1</color>\n\t\t\t<type>{ty}</type>\n\t\t</timemarker>"
                 for f, ty in ((BUILD_IN, 4), (POSTER, 8), (BUILD_OUT, 6)))
    s = s.replace("<timemarkerset/>", f"<timemarkerset>{mk}\n\t</timemarkerset>", 1)
    s = re.sub(r"<currentFrame>[^<]*</currentFrame>", f"<currentFrame>{t(POSTER)}</currentFrame>", s, count=1)

    for must in ('name="Drop Zone" id="311"', 'name="Logo"/>', "<type>6</type>", "Media/logo.png"):
        assert must in s, must
    assert s.count('id="16" flags="8589938704"') == 3
    (d / f"{v['title']}.moti").write_text(s, encoding="utf-8")
    thumbnail(v, d, previews)
    return d


def thumbnail(v, d, previews):
    W, H = v.get("size", (3840, 2160))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    X = lambda x: int(W / 2 + x)
    Y = lambda y: int(H / 2 - y)
    for g in reversed(v["graphics"]):
        fn = media_name(g)
        img = Image.open(d / "Media" / fn)
        im.alpha_composite(img, (X(g["pos"][0]) - img.width // 2, Y(g["pos"][1]) - img.height // 2))
    (lx, ly), sc = v["logo"]
    logo = Image.open(d / "Media" / "logo.png").resize((int(1000 * sc),) * 2, Image.LANCZOS)
    im.alpha_composite(logo, (X(lx) - logo.width // 2, Y(ly) - logo.height // 2))
    dr = ImageDraw.Draw(im)
    labels = {NAME_ID: "Name", TITLE_ID: "Title", COUNCIL_ID: v["text"][COUNCIL_ID][-1]}
    for nid, (font, size, y, rgb, *_r) in v["text"].items():
        dr.text((X(v["text_x"]), Y(y)), labels[nid], font=ImageFont.truetype(FONT, size), fill=rgb, anchor="ls")
    im.resize((W // 6, H // 6), Image.LANCZOS).save(d / "large.png")
    im.resize((W // 20, H // 20), Image.LANCZOS).save(d / "small.png")
    bg = Image.new("RGBA", (W, H), (70, 90, 80, 255))
    bg.alpha_composite(im)
    crop = bg.crop(v.get("preview_crop", (0, 1200, 2600, 2160)))
    slug = v["title"].split("lower third ")[-1].lower().replace(" ", "-")
    crop.resize((crop.width // 2, crop.height // 2), Image.LANCZOS).save(previews / f"{slug}.png")


if __name__ == "__main__":
    base = Path(SRC).read_text(encoding="utf-8")
    for bid in BRANDS if "all" in ARGS.brands else dict.fromkeys(ARGS.brands):
        brand = load_brand(bid)
        previews = PREVIEWS / bid
        previews.mkdir(parents=True, exist_ok=True)
        logo = previews / "logo_square.png"
        square_logo(brand["logo"], logo)
        landscape = variants(brand)
        for v in landscape + [vertical(v) for v in landscape]:
            print("built", build(v, base, logo, OUT_ROOT / brand["category"], previews))
