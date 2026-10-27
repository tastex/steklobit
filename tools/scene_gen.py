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


def area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def ccw(poly):
    return poly if area(poly) > 0 else poly[::-1]


def is_convex(poly):
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = poly[i - 1], poly[i], poly[(i + 1) % n]
        if (bx - ax) * (cy - by) - (by - ay) * (cx - bx) < -1e-6:
            return False
    return True


def inside_tri(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return (d1 > 0 and d2 > 0 and d3 > 0) or (d1 < 0 and d2 < 0 and d3 < 0)


def convex_parts(poly):
    """ear-clip a simple polygon, then greedily merge triangles back into convex pieces"""
    poly = ccw(poly)
    if is_convex(poly):
        return [poly]
    idx = list(range(len(poly)))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 5000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) <= 0:
                continue
            if any(inside_tri(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append([i0, i1, i2])
            idx.pop(k)
            break
    tris.append(idx[:])
    pieces = tris
    merged = True
    while merged:
        merged = False
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                A, B = pieces[i], pieces[j]
                for ka in range(len(A)):
                    u, v = A[ka], A[(ka + 1) % len(A)]
                    if v in B and B[(B.index(v) + 1) % len(B)] == u:
                        kb = B.index(v)
                        cand = A[:ka + 1] + [B[(kb + t) % len(B)] for t in range(2, len(B))] + A[ka + 1:]
                        if is_convex([poly[q] for q in cand]):
                            pieces[i] = cand
                            pieces.pop(j)
                            merged = True
                        break
                if merged:
                    break
            if merged:
                break
    return [[poly[q] for q in p] for p in pieces]


def centroid(poly):
    return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)


def cut(poly, target, depth=0):
    """split a convex polygon with random straight cuts, like nipping glass"""
    if abs(area(poly)) < target * random.uniform(0.7, 1.5) or depth > 14:
        return [poly]
    cx, cy = centroid(poly)
    # cut across the longer side of the piece so shards stay chunky
    best, ang0 = 0, 0
    for i in range(len(poly)):
        for j in range(i + 1, len(poly)):
            d = math.hypot(poly[j][0] - poly[i][0], poly[j][1] - poly[i][1])
            if d > best:
                best, ang0 = d, math.atan2(poly[j][1] - poly[i][1], poly[j][0] - poly[i][0])
    ang = ang0 + random.uniform(-0.6, 0.6)            # cut line normal follows the long axis
    nx, ny = math.cos(ang), math.sin(ang)
    off = random.uniform(-0.25, 0.25) * best
    c = nx * cx + ny * cy + off * 0.5
    left = clip_half(poly, nx, ny, c)
    right = clip_half(poly, -nx, -ny, -c)
    if len(left) < 3 or len(right) < 3 or min(abs(area(left)), abs(area(right))) < target * 0.38:
        return [poly]
    return cut(left, target, depth + 1) + cut(right, target, depth + 1)


def inset(poly, g):
    """offset a convex ccw polygon inwards by g (the grout line)"""
    poly = ccw(poly)
    n = len(poly)
    lines = []
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        nx, ny = -dy / L, dx / L                     # inward normal for ccw
        lines.append((ax + nx * g, ay + ny * g, dx, dy))
    out = []
    for i in range(len(lines)):
        x1, y1, dx1, dy1 = lines[i - 1]
        x2, y2, dx2, dy2 = lines[i]
        den = dx1 * dy2 - dy1 * dx2
        if abs(den) < 1e-9:
            continue
        t = ((x2 - x1) * dy2 - (y2 - y1) * dx2) / den
        out.append((x1 + dx1 * t, y1 + dy1 * t))
    if len(out) < 3 or area(out) <= 0 or not is_convex(out):
        return None
    cx, cy = centroid(poly)
    if any(math.hypot(p[0] - cx, p[1] - cy) > 3 * math.sqrt(abs(area(poly))) for p in out):
        return None
    return out


def shrink(poly, gap):
    cx, cy = centroid(poly)
    r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in poly) / len(poly)
    k = max(0.2, 1 - gap / max(r, 0.1))
    return [(cx + (p[0] - cx) * k, cy + (p[1] - cy) * k) for p in poly]


def ngon(cx, cy, rx, ry, n=14, flat_top=0):
    pts_ = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        if flat_top and y < cy - ry + flat_top:
            y = cy - ry + flat_top
        if not pts_ or math.hypot(x - pts_[-1][0], y - pts_[-1][1]) > 1:
            pts_.append((x, y))
    return pts_


def tint(hex_, k):
    r, g, b = int(hex_[1:3], 16), int(hex_[3:5], 16), int(hex_[5:7], 16)
    mix = lambda v: max(0, min(255, int(v + (255 - v) * k if k > 0 else v * (1 + k))))
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"


uid = 0
defs = []


def shards(shape, colors, step, gap, grout, weights=None):
    """a grouted patch of glass: the shape is nipped into shards whose outer edges follow its outline"""
    target = step * step * 1.3
    base = []
    body = []
    for part in convex_parts(shape):
        base.append(f'<polygon points="{pts(part)}" fill="{grout}"/>')
        for piece in cut(part, target):
            sh = inset(piece, gap / 2) or shrink(piece, gap / 2)
            col = random.choices(colors, weights=weights)[0] if weights else random.choice(colors)
            col = tint(col, random.uniform(-0.08, 0.08))
            body.append(f'<polygon points="{pts(sh)}" fill="{col}"/>')
            # a thin sheen on some shards, like light catching the glass
            if len(sh) >= 3 and random.random() < 0.35:
                a, b = sh[0], sh[1]
                cx, cy = centroid(sh)
                streak = [a, b, ((b[0] * 2 + cx) / 3, (b[1] * 2 + cy) / 3), ((a[0] * 2 + cx) / 3, (a[1] * 2 + cy) / 3)]
                body.append(f'<polygon points="{pts(streak)}" fill="#fff" fill-opacity=".14"/>')
    return f'<g>{"".join(base)}{"".join(body)}</g>'


def anim_rotate(angles, cx, cy):
    vals = ";".join(f"{f(a)} {f(cx)} {f(cy)}" for a in angles)
    return f'<animateTransform attributeName="transform" type="rotate" values="{vals}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'


def anim_translate(offs):
    vals = ";".join(f"{f(x)} {f(y)}" for x, y in offs)
    return f'<animateTransform attributeName="transform" type="translate" values="{vals}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'


def anim_scale(scales):
    vals = ";".join(f"{f(sx)} {f(sy)}" for sx, sy in scales)
    return f'<animateTransform attributeName="transform" type="scale" values="{vals}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'


def breathe(k, period):
    """smooth swell and back (not stop-motion), so breathing reads as calm"""
    return (f'<animateTransform attributeName="transform" type="scale" values="1 1;{f(k)} {f(k)};1 1" keyTimes="0;0.5;1" '
            f'calcMode="spline" keySplines=".42 0 .58 1;.42 0 .58 1" dur="{f(period)}s" repeatCount="indefinite"/>')


def about(inner_anim, cx, cy, inner):
    """apply a scale animation around the point (cx, cy)"""
    return f'<g transform="translate({f(cx)} {f(cy)})"><g>{inner_anim}<g transform="translate({f(-cx)} {f(-cy)})">{inner}</g></g></g>'


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


NECK, NECK_X = (85, 88), 215   # indices in dragon_shards.json; mirror line for the left-looking pose


def dragon():
    """traced from Vladimir's photos of the dragon mosaic: dragon_shards.json is every piece of the first photo
    (looking right), dragon_pose2.json the head from the second photo (looking left) plus light filler glass
    for the spot the right-looking head leaves bare"""
    import json, os
    here = os.path.dirname(os.path.abspath(__file__))
    data = json.load(open(os.path.join(here, "dragon_shards.json")))
    pose2 = json.load(open(os.path.join(here, "dragon_pose2.json")))
    groups = {"bg": [], "head": [], "body": [], "wing": [], "tail": [], "legs": []}
    neck = ""
    for i, sh in enumerate(data["polys"]):
        if i in NECK:   # two neck pieces on the left: they swap sides together with the head
            neck += f'<polygon points="{pts(sh["p"])}" fill="{sh["c"]}"/>'
            continue
        groups[sh["part"]].append(f'<polygon points="{pts(sh["p"])}" fill="{sh["c"]}"/>')
    g = {k: "".join(v) for k, v in groups.items()}
    filler = "".join(f'<polygon points="{pts(sh["p"])}" fill="{sh["c"]}"/>' for sh in pose2["filler"])
    head2 = "".join(f'<polygon points="{pts(sh["p"])}" fill="{sh["c"]}"/>' for sh in pose2["head"])
    # as in the video the head is re-laid in one go: looking left for frames 0-5 and 13-17, right for 6-12
    left = [i < 6 or i > 12 for i in range(len(SEQ))]

    def shown(on):
        keys = [0] + [i for i in range(1, len(on)) if on[i] != on[i - 1]]
        vals = ";".join("visible" if on[k] else "hidden" for k in keys)
        times = ";".join(f"{k / len(on):.4f}" for k in keys)
        return f'<animate attributeName="visibility" values="{vals}" keyTimes="{times}" dur="{f(DUR)}s" calcMode="discrete" repeatCount="indefinite"/>'
    neck2 = f'<g transform="translate({2 * NECK_X} 0) scale(-1 1)">{neck}</g>'
    head_g = (f'<g>{shown([not l for l in left])}{g["head"]}{neck}</g>'
              f'<g>{shown(left)}{neck2}{head2}</g>')
    # the rest stays the glass of the first photo, nudged a little every frame
    wing_g = rot_group(g["wing"], 12, -16, 352, 292)
    tail_g = rot_group(g["tail"], -7, 9, 300, 360)
    legs_g = rot_group(g["legs"], -5, 5, 220, 400)
    figure = rot_group(tail_g + legs_g + g["body"] + wing_g, -2, 2, 240, 450)
    return f'<rect width="500" height="500" fill="{data["grout"]}"/>{g["bg"]}{filler}{figure}{head_g}'


# ---------- tiger (local 520x520 window) ----------
TURQ = ["#38b7cf", "#2aa3c4", "#55c8dc", "#1f8fb3", "#46bfd6"]
LAV = ["#9a98c4", "#b4b3d6", "#7f7fb0", "#c9c7e2"]
ORANGE = ["#e2622a", "#c94a1f", "#ec7a38", "#b8401c", "#f08a40", "#1b1310", "#2a1a12", "#9c2a1e", "#d8a03a"]
OW = [4, 3, 3, 2, 2, 2, 1, 2, 1]
CAMO = ["#8a7a32", "#b0902e", "#6e6428", "#d8a03a", "#4f4a22", "#1b1310", "#c47a2a"]
CW = [3, 3, 2, 2, 2, 2, 1]
T_GROUT = "#1a1410"


def tiger():
    """traced from Vladimir's photo of the tiger mosaic: tiger_shards.json holds every shard (523x523 px)"""
    import json, os
    data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiger_shards.json")))
    groups = {"bg": [], "head": [], "body": [], "tail": []}
    for sh in data["polys"]:
        groups[sh["part"]].append(f'<polygon points="{pts(sh["p"])}" fill="{sh["c"]}"/>')
    g = {k: "".join(v) for k, v in groups.items()}
    head_g = rot_group(g["head"], -4, 4, 180, 440)
    tail_g = rot_group(g["tail"], -6, 5, 452, 120)
    # breathing: only the body swells a little, the head stays as it is
    body_g = about(breathe(1.045, DUR * 2), 360, 262, g["body"])
    return (f'<g transform="scale({520 / 523:.4f})"><rect width="523" height="523" fill="{data["grout"]}"/>'
            f'{g["bg"]}{tail_g}{body_g}{head_g}</g>')


# ---------- wall ----------
def board(x0, y0, x1, y1, hx0, hx1, hy, hole, wood, deep, win):
    r = 14
    F, R = 46, 24     # cutting-board shape: wide fillets where the handle meets the board, rounded handle top
    path = (f"M{x0 + r},{y0} H{hx0 - F} Q{hx0},{y0} {hx0},{y0 - F} V{hy + R} Q{hx0},{hy} {hx0 + R},{hy} H{hx1 - R} Q{hx1},{hy} {hx1},{hy + R} V{y0 - F} Q{hx1},{y0} {hx1 + F},{y0} "
            f"H{x1 - r} Q{x1},{y0} {x1},{y0 + r} V{y1 - r} Q{x1},{y1} {x1 - r},{y1} H{x0 + r} Q{x0},{y1} {x0},{y1 - r} V{y0 + r} Q{x0},{y0} {x0 + r},{y0} Z")
    gid = f"w{x0}"
    defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{wood}"/><stop offset="1" stop-color="{deep}"/></linearGradient>')
    grain = "".join(f'<path d="M{x0 + 8},{y} q{(x1 - x0) / 3},{random.uniform(-6, 6)} {x1 - x0 - 16},{random.uniform(-4, 4)}" stroke="{deep}" stroke-opacity=".35" stroke-width="{random.uniform(1, 2.5):.1f}" fill="none"/>'
                    for y in range(int(y0) + 20, int(y1) - 10, 26))
    wx0, wy0, wx1, wy1 = win
    return (f'<g><path d="{path}" transform="translate(6 10)" fill="#2a1a10" fill-opacity=".22"/><path d="{path}" fill="url(#{gid})"/>{grain}'
            f'<circle cx="{hole[0]}" cy="{hole[1]}" r="12" fill="#3b2a1c"/>'
            f'<rect x="{wx0 - 6}" y="{wy0 - 6}" width="{wx1 - wx0 + 12}" height="{wy1 - wy0 + 12}" rx="4" fill="{deep}"/></g>')


def card(x, y, w, h, rot, fill, extra=""):
    return (f'<g transform="rotate({rot} {x + w / 2} {y + h / 2})"><rect x="{x + 3}" y="{y + 5}" width="{w}" height="{h}" rx="3" fill="#2a1a10" fill-opacity=".18"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}"/>{extra}</g>')


def pin(x, y, rot, color="#d9b27c", dark="#a98252"):
    return (f'<g transform="rotate({rot} {x} {y})"><rect x="{x - 9}" y="{y - 60}" width="18" height="120" rx="4" fill="{color}"/>'
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
