"""Vector remake of the Steklobit background: Vladimir's wall with the dragon and tiger mosaics.

Output: scene.svg (1620x1080, same framing as animation.mp4). The mosaics are Voronoi shards
clipped to hand-traced part shapes; parts move in discrete stop-motion poses (SMIL, 7.5 fps,
ping-pong over 10 poses = 2.4 s), like the original video.
"""
import math, random

random.seed(7)
W, H = 1620, 1080
FPS_STEP = 0.4 / 3            # one pose every 4 video frames at 29.97 fps
SEQ = [0, 1, 0] + list(range(2, 10)) + list(range(8, 1, -1))   # observed pose order, 18 keys
DUR = len(SEQ) * FPS_STEP


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def pts(poly):
    return " ".join(f"{f(x)},{f(y)}" for x, y in poly)


# ---------- geometry ----------
def clip_half(poly, a, b, c):
    """keep a*x + b*y <= c"""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def voronoi(x0, y0, x1, y1, step, jitter=0.45):
    seeds = []
    y = y0 - step / 2
    row = 0
    while y < y1 + step:
        x = x0 - step / 2 + (step / 2 if row % 2 else 0)
        while x < x1 + step:
            seeds.append((x + random.uniform(-1, 1) * step * jitter, y + random.uniform(-1, 1) * step * jitter))
            x += step
        y += step * 0.87
        row += 1
    cells = []
    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i, (px, py) in enumerate(seeds):
        if not (x0 - step < px < x1 + step and y0 - step < py < y1 + step):
            continue
        poly = box[:]
        for j, (qx, qy) in enumerate(seeds):
            if i == j or abs(qx - px) > step * 2.6 or abs(qy - py) > step * 2.6:
                continue
            a, b = qx - px, qy - py
            c = (qx * qx + qy * qy - px * px - py * py) / 2
            poly = clip_half(poly, a, b, c)
            if not poly:
                break
        if len(poly) >= 3:
            cells.append(poly)
    return cells


def shrink(poly, gap):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in poly) / len(poly)
    k = max(0.2, 1 - gap / max(r, 0.1))
    return [(cx + (p[0] - cx) * k, cy + (p[1] - cy) * k) for p in poly]


def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


uid = 0
defs = []


def shards(shape, colors, step, gap, grout, weights=None):
    """shape is a polygon (list) or ('circle', cx, cy, r); returns svg for a grouted mosaic patch"""
    global uid
    uid += 1
    cid = f"c{uid}"
    if isinstance(shape, tuple):
        _, cx, cy, r = shape
        defs.append(f'<clipPath id="{cid}"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"/></clipPath>')
        bb = (cx - r, cy - r, cx + r, cy + r)
        base = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{grout}"/>'
    else:
        defs.append(f'<clipPath id="{cid}"><polygon points="{pts(shape)}"/></clipPath>')
        bb = bbox(shape)
        base = f'<polygon points="{pts(shape)}" fill="{grout}"/>'
    body = []
    for cell in voronoi(*bb, step):
        col = random.choices(colors, weights=weights)[0] if weights else random.choice(colors)
        body.append(f'<polygon points="{pts(shrink(cell, gap))}" fill="{col}"/>')
    return f'<g>{base}<g clip-path="url(#{cid})">{"".join(body)}</g></g>'


def anim_rotate(angles, cx, cy):
    vals = ";".join(f"{f(a)} {f(cx)} {f(cy)}" for a in angles)
    return f'<animateTransform attributeName="transform" type="rotate" values="{vals}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'


def anim_translate(offs):
    vals = ";".join(f"{f(x)} {f(y)}" for x, y in offs)
    return f'<animateTransform attributeName="transform" type="translate" values="{vals}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'


def anim_scale(scales):
    vals = ";".join(f"{f(sx)} {f(sy)}" for sx, sy in scales)
    return f'<animateTransform attributeName="transform" type="scale" values="{vals}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'


def poses(fn):
    return [fn(p / 9) for p in SEQ]


def lerp(a, b, u):
    return a + (b - a) * u


def ease(u):
    return 0.5 - 0.5 * math.cos(math.pi * u)


def rot_group(inner, a0, a1, cx, cy):
    return f'<g>{anim_rotate(poses(lambda u: lerp(a0, a1, ease(u))), cx, cy)}{inner}</g>'


# ---------- dragon (local 500x500 window) ----------
GREEN = ["#1d5a33", "#123f24", "#2c7444", "#0f3320", "#245f3a", "#173d28"]
RED = ["#b3202c", "#8e1622", "#c8323a"]
D_GROUT = "#e4e9f1"


def dragon():
    bg = shards([(0, 0), (500, 0), (500, 500), (0, 500)],
                ["#e9eef6", "#dfe4f0", "#f4f6fa", "#d6dcec", "#ccd3e6", "#eef0f7"], 70, 3, "#c9cfde")
    tail = shards([(196, 340), (262, 346), (324, 376), (384, 408), (402, 432), (382, 458), (316, 452), (254, 432), (198, 404)], GREEN, 34, 2.4, D_GROUT) \
        + shards([(368, 414), (410, 402), (428, 430), (406, 462), (370, 455)], RED, 26, 2.2, D_GROUT)
    leg1 = shards([(165, 378), (202, 384), (196, 440), (176, 452), (148, 446), (166, 420)], GREEN, 28, 2.2, D_GROUT)
    leg2 = shards([(238, 392), (276, 388), (292, 446), (266, 462), (244, 456)], GREEN, 28, 2.2, D_GROUT)
    body = shards([(105, 188), (180, 212), (240, 238), (282, 300), (272, 360), (222, 392), (160, 386), (110, 352), (74, 300), (68, 248)], GREEN, 36, 2.4, D_GROUT)
    for spike in ([(76, 232), (50, 248), (82, 256)], [(70, 270), (44, 286), (76, 294)], [(72, 306), (48, 324), (82, 328)]):
        body += shards(spike, GREEN, 22, 2, D_GROUT)
    wing = shards([(226, 236), (300, 232), (372, 250), (436, 266), (470, 286), (432, 310), (362, 334), (290, 346), (244, 318)], GREEN, 34, 2.4, D_GROUT)
    head = shards([(95, 110), (130, 84), (176, 74), (216, 94), (232, 140), (216, 190), (180, 216), (140, 206), (104, 176), (88, 140)], GREEN, 34, 2.4, D_GROUT)
    head += shards([(38, 94), (100, 104), (102, 142)], RED, 24, 2, D_GROUT)
    for crest in ([(148, 82), (158, 42), (178, 84)], [(178, 82), (194, 58), (204, 94)], [(202, 94), (226, 80), (214, 114)]):
        head += shards(crest, RED, 22, 2, D_GROUT)
    head += f'<circle cx="138" cy="128" r="9" fill="{D_GROUT}"/><circle cx="138" cy="128" r="5.5" fill="#f7f9fc"/>'

    # head: sways and turns its beak from left to right half-way through the move
    head_turn = f'<g>{anim_translate([(160, 140)] * len(SEQ))}<g>{anim_scale(poses(lambda u: (1 if u < 0.5 else -1, 1)))}<g transform="translate(-160 -140)">{head}</g></g></g>'
    head_g = rot_group(head_turn, -14, 12, 172, 205)
    wing_g = rot_group(wing, 12, -22, 246, 282)
    tail_g = rot_group(tail, -10, 12, 212, 372)
    leg1_g = rot_group(leg1, -8, 6, 182, 384)
    leg2_g = rot_group(leg2, 6, -8, 256, 392)
    figure = rot_group(tail_g + leg1_g + leg2_g + body + wing_g + head_g, -5, 5, 200, 440)
    return bg + figure


# ---------- tiger (local 520x520 window) ----------
TURQ = ["#38b7cf", "#2aa3c4", "#55c8dc", "#1f8fb3", "#46bfd6"]
LAV = ["#9a98c4", "#b4b3d6", "#7f7fb0", "#c9c7e2"]
ORANGE = ["#e2622a", "#c94a1f", "#ec7a38", "#b8401c", "#f08a40", "#1b1310", "#2a1a12", "#9c2a1e", "#d8a03a"]
OW = [4, 3, 3, 2, 2, 2, 1, 2, 1]
CAMO = ["#8a7a32", "#b0902e", "#6e6428", "#d8a03a", "#4f4a22", "#1b1310", "#c47a2a"]
CW = [3, 3, 2, 2, 2, 2, 1]
T_GROUT = "#1a1410"


def tiger():
    bg = shards([(0, 0), (520, 0), (520, 520), (0, 520)], TURQ, 80, 3.5, "#0f2f3a") \
        + shards([(0, 0), (520, 0), (520, 60), (300, 90), (0, 70)], LAV, 60, 3, "#2a2a40")
    body = shards([(250, 110), (340, 94), (430, 110), (490, 170), (496, 262), (470, 340), (420, 382), (340, 382), (298, 330), (296, 200)], CAMO, 40, 3, T_GROUT, CW)
    tail = shards([(438, 138), (482, 150), (508, 222), (508, 332), (492, 422), (462, 432), (474, 330), (470, 222), (452, 172)], ["#e2622a", "#ec7a38", "#c94a1f", "#f08a40"], 34, 3, T_GROUT)
    head = shards([(35, 140), (110, 110), (190, 95), (260, 120), (300, 200), (312, 290), (292, 362), (232, 402), (120, 412), (58, 382), (28, 300), (24, 210)], ORANGE, 36, 3, T_GROUT, OW)
    head += shards([(18, 108), (60, 92), (106, 108), (96, 152), (44, 152)], ["#e2622a", "#f08a40", "#c94a1f"], 28, 2.6, T_GROUT)
    head += shards([(184, 84), (250, 78), (272, 110), (236, 142), (194, 126)], ["#e2622a", "#f08a40", "#c94a1f"], 28, 2.6, T_GROUT)
    head += shards([(200, 300), (282, 290), (332, 330), (322, 392), (250, 402), (206, 360)], ["#8e1622", "#b3202c", "#6e1018", "#2a3a8a"], 30, 2.6, T_GROUT, [4, 3, 2, 1])
    teeth = ""
    for i, x in enumerate(range(72, 340, 34)):
        h = 58 if i % 2 == 0 else 48
        teeth += f'<polygon points="{pts([(x, 384), (x + 28, 380), (x + 26, 384 + h), (x + 4, 386 + h)])}" fill="{random.choice(["#f1e6cc", "#e8d8b4", "#f7efdc"])}" stroke="{T_GROUT}" stroke-width="3"/>'
    eyes = "".join(f'<ellipse cx="{x}" cy="{y}" rx="34" ry="38" fill="{T_GROUT}"/><ellipse cx="{x}" cy="{y}" rx="29" ry="33" fill="#f2f7fb"/>' for x, y in ((112, 282), (180, 274)))
    pupils = f'<g>{anim_translate(poses(lambda u: (lerp(-6, 6, ease(u)), lerp(2, -2, ease(u)))))}' \
             + "".join(f'<circle cx="{x}" cy="{y + 6}" r="9" fill="#1b1310"/>' for x, y in ((112, 282), (180, 274))) + "</g>"
    head_g = rot_group(head + teeth + eyes + pupils, -7, 7, 190, 400)
    tail_g = rot_group(tail, -14, 12, 458, 150)
    breathe = f'<g>{anim_translate([(390, 380)] * len(SEQ))}<g>{anim_scale(poses(lambda u: (1, lerp(0.97, 1.04, ease(u)))))}<g transform="translate(-390 -380)">{body}</g></g></g>'
    return bg + tail_g + breathe + head_g


# ---------- wall ----------
def board(x0, y0, x1, y1, hx0, hx1, hy, hole, wood, deep, win):
    r = 14
    path = (f"M{x0 + r},{y0} H{hx0} V{hy + 24} Q{hx0},{hy} {hx0 + 24},{hy} H{hx1 - 24} Q{hx1},{hy} {hx1},{hy + 24} V{y0} "
            f"H{x1 - r} Q{x1},{y0} {x1},{y0 + r} V{y1 - r} Q{x1},{y1} {x1 - r},{y1} H{x0 + r} Q{x0},{y1} {x0},{y1 - r} V{y0 + r} Q{x0},{y0} {x0 + r},{y0} Z")
    gid = f"w{x0}"
    defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{wood}"/><stop offset="1" stop-color="{deep}"/></linearGradient>')
    grain = "".join(f'<path d="M{x0 + 8},{y} q{(x1 - x0) / 3},{random.uniform(-6, 6)} {x1 - x0 - 16},{random.uniform(-4, 4)}" stroke="{deep}" stroke-opacity=".35" stroke-width="{random.uniform(1, 2.5):.1f}" fill="none"/>'
                    for y in range(int(y0) + 20, int(y1) - 10, 26))
    wx0, wy0, wx1, wy1 = win
    return (f'<g filter="url(#shadow)"><path d="{path}" fill="url(#{gid})"/>{grain}'
            f'<circle cx="{hole[0]}" cy="{hole[1]}" r="12" fill="#3b2a1c"/>'
            f'<rect x="{wx0 - 6}" y="{wy0 - 6}" width="{wx1 - wx0 + 12}" height="{wy1 - wy0 + 12}" rx="4" fill="{deep}"/></g>')


def card(x, y, w, h, rot, fill, extra=""):
    return f'<g transform="rotate({rot} {x + w / 2} {y + h / 2})" filter="url(#soft)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}"/>{extra}</g>'


def pin(x, y, rot, color="#d9b27c", dark="#a98252"):
    return (f'<g transform="rotate({rot} {x} {y})" filter="url(#soft)"><rect x="{x - 9}" y="{y - 60}" width="18" height="120" rx="4" fill="{color}"/>'
            f'<rect x="{x - 1}" y="{y - 60}" width="2" height="120" fill="{dark}"/><rect x="{x - 10}" y="{y - 8}" width="20" height="10" fill="{dark}" opacity=".6"/></g>')


def leaves():
    out = ['<rect x="1462" y="60" width="170" height="1030" fill="#f2c9a6"/>',
           '<rect x="1462" y="60" width="170" height="1030" fill="none" stroke="#e7b48c" stroke-width="10"/>',
           '<path d="M1560,1080 C1480,900 1600,760 1520,600 S1560,300 1500,90" stroke="#3a2a1c" stroke-width="5" fill="none"/>']
    for i in range(16):
        t = i / 15
        x = 1500 + 50 * math.sin(t * 7)
        y = 1060 - t * 960
        a = (-40 if i % 2 else 40) + random.uniform(-15, 15)
        col = random.choice(["#2f2a22", "#7a2a1e", "#c9562a", "#4e5a2e", "#e08a52"])
        out.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="42" ry="15" transform="rotate({f(a)} {f(x)} {f(y)})" fill="{col}" stroke="#2a1c12" stroke-width="3"/>')
    return "".join(out)


def post(x0, x1, light, dark):
    out = [f'<rect x="{x0}" y="-2000" width="{x1 - x0}" height="{H + 4000}" fill="{light}"/>']
    for _ in range(26):
        x = random.uniform(x0, x1)
        out.append(f'<path d="M{f(x)},0 L{f(x + random.uniform(-12, 12))},{H}" stroke="{dark}" stroke-opacity="{random.uniform(.15, .45):.2f}" stroke-width="{random.uniform(2, 9):.1f}"/>')
    for _ in range(10):
        out.append(f'<ellipse cx="{f(random.uniform(x0, x1))}" cy="{f(random.uniform(0, H))}" rx="{f(random.uniform(6, 22))}" ry="{f(random.uniform(20, 70))}" fill="{dark}" opacity=".35"/>')
    return "".join(out)


def scene():
    parts = []
    parts.append('<rect x="-3000" y="-3000" width="7620" height="7080" fill="#e2ded7"/><rect width="1620" height="1080" fill="url(#wall)"/>')
    parts.append(post(0, 110, "#5a3a26", "#2a1a10"))
    parts.append(post(145, 325, "#9a8a78", "#4a3a2c"))
    parts.append(post(1335, 1445, "#5a3a26", "#2a1a10"))
    parts.append(leaves())
    # blue doodle flowers on the wall
    doodle = ""
    for cx, cy in ((930, 690), (1235, 570), (1140, 740), (840, 640)):
        for k in range(5):
            a = k * 72
            doodle += f'<ellipse cx="{cx}" cy="{cy - 16}" rx="10" ry="16" transform="rotate({a} {cx} {cy})"/>'
    parts.append(f'<g fill="none" stroke="#5b86b8" stroke-width="2.5" opacity=".75">{doodle}'
                 '<path d="M760,620 C820,560 900,600 880,660 M1180,720 C1250,690 1320,700 1340,680 M1100,780 C1150,760 1220,770 1260,740"/></g>')
    # postcards
    parts.append(card(268, -8, 272, 230, 2, "url(#sky)", '<path d="M300,200 C330,90 380,40 430,70 C470,100 480,160 500,200" fill="#f3e2a6" opacity=".75"/>'))
    parts.append(card(440, 10, 330, 330, -12, "url(#dusk)",
                      '<text x="520" y="150" font-family="Marck Script, cursive" font-size="44" fill="#f4e9ef" transform="rotate(8 560 150)">Владимир</text>'))
    parts.append(card(720, 0, 220, 160, -6, "#2b2f3a"))
    parts.append(card(905, 285, 275, 375, 2, "#121418",
                      '<rect x="1060" y="520" width="80" height="70" fill="#c9a05a" opacity=".6"/>'))
    parts.append(card(1082, 80, 265, 380, 1, "url(#lamps)",
                      '<text x="1150" y="400" font-family="Marck Script, cursive" font-size="42" fill="#f4f1ea" transform="rotate(-8 1200 400)">Владимир</text>'
                      '<circle cx="1110" cy="200" r="26" fill="#3a4250"/><circle cx="1300" cy="250" r="22" fill="#3a4250"/><circle cx="1240" cy="290" r="30" fill="#2a3240"/>'))
    parts.append(card(400, 465, 240, 190, -1, "#f3efe4"))
    parts.append(card(10, 490, 300, 400, -14, "#f6f4ef",
                      '<rect x="40" y="520" width="240" height="140" fill="url(#dusk)"/><rect x="40" y="670" width="115" height="150" fill="#3e5f9c"/>'
                      '<rect x="165" y="670" width="115" height="150" fill="#2a2e36"/>'
                      '<text x="70" y="865" font-family="Marck Script, cursive" font-size="30" fill="#4a4a5a">Владимир ♡</text>'))
    # twine
    parts.append('<path d="M0,430 C200,480 420,520 560,500 S700,440 740,430" stroke="#b89a6a" stroke-width="5" fill="none"/>'
                 '<path d="M820,40 C1000,60 1200,90 1370,110" stroke="#b89a6a" stroke-width="5" fill="none"/>'
                 '<path d="M1080,260 L1370,110" stroke="#b89a6a" stroke-width="4" fill="none"/>')
    # boards with mosaics
    parts.append(board(732, 225, 1085, 580, 862, 962, 105, (910, 140), "#e6aa2e", "#b9801c", (785, 280, 1035, 530)))
    defs.append('<clipPath id="winD"><rect width="500" height="500"/></clipPath><clipPath id="winT"><rect width="520" height="520"/></clipPath>')
    parts.append(f'<g transform="translate(785 280) scale(.5)"><g clip-path="url(#winD)">{dragon()}</g></g>')
    parts.append(board(362, 638, 720, 990, 505, 592, 515, (548, 552), "#7a3a1c", "#4a200c", (418, 684, 678, 944)))
    parts.append(f'<g transform="translate(418 684) scale(.5)"><g clip-path="url(#winT)">{tiger()}</g></g>')
    # clothespins on top
    parts.append(pin(198, 440, 12) + pin(538, 470, -14) + pin(910, 70, 4) + pin(1058, 205, 2)
                 + pin(1210, 80, -10, "#2f5fb0", "#1d3f80") + pin(704, 418, -40, "#c42a2a", "#8a1a1a"))
    return "".join(parts)


body = scene()
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Стена с мозаиками: дракон и тигр в деревянных рамках">
<defs>
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8e5df"/><stop offset="1" stop-color="#dcd6cc"/></linearGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5d8fd6"/><stop offset="1" stop-color="#3a6bb8"/></linearGradient>
<linearGradient id="dusk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3f5a"/><stop offset=".45" stop-color="#c8786a"/><stop offset=".6" stop-color="#4a4a52"/><stop offset="1" stop-color="#25272c"/></linearGradient>
<linearGradient id="lamps" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2c4366"/><stop offset="1" stop-color="#3f6a8f"/></linearGradient>
<filter id="shadow" x="-10%" y="-10%" width="130%" height="130%"><feDropShadow dx="6" dy="10" stdDeviation="8" flood-color="#2a1a10" flood-opacity=".35"/></filter>
<filter id="soft" x="-10%" y="-10%" width="130%" height="130%"><feDropShadow dx="3" dy="5" stdDeviation="4" flood-color="#2a1a10" flood-opacity=".28"/></filter>
{"".join(defs)}
</defs>
{body}
</svg>'''
open("scene.svg", "w").write(svg)
print(len(svg), "bytes", f"{DUR:.2f}s loop")
