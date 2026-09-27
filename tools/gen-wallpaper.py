#!/usr/bin/env python3
"""Procedural PLACEHOLDER wallpaper: moonlit violet xianxia landscape with a
lone robed cultivator silhouette on a cliff. Not Wang Lin artwork — replace
with licensed / your own art (see README "Wallpaper").

Usage: gen-wallpaper.py [WIDTH HEIGHT] [OUT.png]   (default 1920 1080)
Needs: python3, rsvg-convert (librsvg).
"""
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = json.loads((ROOT / "palette.json").read_text())
args = sys.argv[1:]
W, H = (int(args[0]), int(args[1])) if len(args) >= 2 else (1920, 1080)
OUT = Path(args[2]) if len(args) >= 3 else ROOT / "wallpapers" / "wanglin-placeholder.png"
S = W / 1920  # scale factor; design coordinates are 1920x1080
rng = random.Random(7)


def ridge(y0, rough, n=9, x0=-50, x1=1970):
    """Midpoint-displacement ridgeline -> list of (x, y) in design coords."""
    pts = [(x0, y0 + rng.uniform(-rough, rough)), (x1, y0 + rng.uniform(-rough, rough))]
    r = rough
    for _ in range(n):
        new = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            new.append((ax, ay))
            new.append(((ax + bx) / 2, (ay + by) / 2 + rng.uniform(-r, r)))
        new.append(pts[-1])
        pts = new
        r *= 0.55
    return pts


def poly(pts, fill, extra=""):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polygon points="{d} 1970,1130 -50,1130" fill="{fill}" {extra}/>'


def peaks(pts, cx, spread, height):
    """Lift a ridge into a mountain massif around cx."""
    out = []
    for x, y in pts:
        t = max(0.0, 1 - abs(x - cx) / spread)
        out.append((x, y - height * t ** 1.6))
    return out


def pagoda(x, y, s, fill):
    """Tiered pagoda silhouette with upturned eaves, base at (x, y)."""
    parts = []
    tiers, w, h = 5, 60 * s, 22 * s
    cy = y
    for i in range(tiers):
        tw = w * (1 - i * 0.14)
        parts.append(f'<rect x="{x - tw * 0.32:.1f}" y="{cy - h:.1f}" width="{tw * 0.64:.1f}" height="{h:.1f}" fill="{fill}"/>')
        ey = cy - h
        parts.append(
            f'<path d="M{x - tw * 0.62:.1f},{ey - 2 * s:.1f} Q{x - tw * 0.3:.1f},{ey + 3 * s:.1f} {x:.1f},{ey - 9 * s:.1f} '
            f'Q{x + tw * 0.3:.1f},{ey + 3 * s:.1f} {x + tw * 0.62:.1f},{ey - 2 * s:.1f} L{x:.1f},{ey - 14 * s:.1f} Z" fill="{fill}"/>')
        cy = ey - 8 * s
    parts.append(f'<rect x="{x - 1.5 * s:.1f}" y="{cy - 26 * s:.1f}" width="{3 * s:.1f}" height="{26 * s:.1f}" fill="{fill}"/>')
    return "\n".join(parts)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 1920 1080">']
svg.append(f"""
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#06030B"/>
    <stop offset="0.45" stop-color="{P['base']}"/>
    <stop offset="0.75" stop-color="#241335"/>
    <stop offset="1" stop-color="#2E1845"/>
  </linearGradient>
  <radialGradient id="moon" cx="0.42" cy="0.40" r="0.62">
    <stop offset="0" stop-color="#EDE3FB"/>
    <stop offset="0.6" stop-color="#C7B0EA"/>
    <stop offset="1" stop-color="#8E6BC0"/>
  </radialGradient>
  <radialGradient id="halo">
    <stop offset="0" stop-color="{P['lavender']}" stop-opacity="0.55"/>
    <stop offset="0.35" stop-color="{P['purple']}" stop-opacity="0.28"/>
    <stop offset="1" stop-color="{P['purple']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="aura">
    <stop offset="0" stop-color="{P['lavender']}" stop-opacity="0.65"/>
    <stop offset="0.4" stop-color="{P['purple']}" stop-opacity="0.30"/>
    <stop offset="1" stop-color="{P['purple']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="vignette" cx="0.62" cy="0.45" r="0.85">
    <stop offset="0.45" stop-color="#000" stop-opacity="0"/>
    <stop offset="1" stop-color="#000" stop-opacity="0.72"/>
  </radialGradient>
  <linearGradient id="leftveil" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{P['mantle']}" stop-opacity="0.75"/>
    <stop offset="0.45" stop-color="{P['mantle']}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="mistgrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#C9B5EE" stop-opacity="0"/>
    <stop offset="0.5" stop-color="#C9B5EE" stop-opacity="0.22"/>
    <stop offset="1" stop-color="#C9B5EE" stop-opacity="0"/>
  </linearGradient>
  <filter id="nebula" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.0022 0.0045" numOctaves="5" seed="11"/>
    <feColorMatrix type="matrix" values="0 0 0 0 0.43  0 0 0 0 0.25  0 0 0 0 0.63  0 0 0 1.6 -0.75"/>
    <feGaussianBlur stdDeviation="6"/>
  </filter>
  <filter id="moontex">
    <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" seed="3"/>
    <feColorMatrix type="matrix" values="0 0 0 0 0.35  0 0 0 0 0.25  0 0 0 0 0.55  0 0 0 0.9 -0.35"/>
    <feComposite in2="SourceGraphic" operator="in"/>
  </filter>
  <filter id="blur8"><feGaussianBlur stdDeviation="8"/></filter>
  <filter id="blur30"><feGaussianBlur stdDeviation="30"/></filter>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="softglow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2.2"/>
  </filter>
</defs>
<rect width="1920" height="1080" fill="url(#sky)"/>
<rect width="1920" height="1080" filter="url(#nebula)" opacity="0.85"/>
""")

# Stars
for _ in range(260):
    x, y = rng.uniform(0, 1920), rng.uniform(0, 620)
    r = rng.choice([0.6, 0.8, 1.0, 1.3])
    svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#E8DDFB" opacity="{rng.uniform(0.25, 0.8):.2f}"/>')

# Moon + halo, right of centre
MX, MY, MR = 1360, 330, 150
svg.append(f'<circle cx="{MX}" cy="{MY}" r="{MR * 3.4}" fill="url(#halo)"/>')
svg.append(f'<circle cx="{MX}" cy="{MY}" r="{MR}" fill="url(#moon)"/>')
svg.append(f'<circle cx="{MX}" cy="{MY}" r="{MR}" fill="#fff" filter="url(#moontex)" opacity="0.55"/>')
svg.append(f'<circle cx="{MX}" cy="{MY}" r="{MR + 3}" fill="none" stroke="#F2ECFA" stroke-opacity="0.35" stroke-width="2" filter="url(#softglow)"/>')

# Far mountains (misty), with a massif behind the moon
far = peaks(ridge(640, 60), 1180, 520, 170)
far = peaks(far, 420, 160, 150)
far = peaks(far, 760, 120, 110)
spires = peaks(peaks(ridge(700, 30, n=10), 1030, 70, 260), 1880, 90, 230)
svg.append(poly(spires, "#2F1D47", 'opacity="0.7"'))
svg.append(poly(far, "#3A2656", 'opacity="0.55"'))
svg.append(f'<rect x="0" y="560" width="1920" height="200" fill="url(#mistgrad)" filter="url(#blur30)"/>')

mid = peaks(ridge(720, 70), 1560, 420, 150)
svg.append(poly(mid, "#2A1840", 'opacity="0.85"'))

# Pagodas on the mid ridge
def ridge_y(pts, x):
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if ax <= x <= bx:
            return ay + (by - ay) * (x - ax) / (bx - ax)
    return pts[-1][1]

for px, s in ((1540, 1.25), (1650, 0.9), (1745, 1.05)):
    svg.append(pagoda(px, ridge_y(mid, px) + 8, s, "#1C1029"))
    # lantern glows
    svg.append(f'<circle cx="{px}" cy="{ridge_y(mid, px) - 40 * s:.0f}" r="{3 * s:.1f}" fill="{P["lavender"]}" filter="url(#glow)" opacity="0.8"/>')

svg.append(f'<rect x="-50" y="700" width="2020" height="160" fill="url(#mistgrad)" filter="url(#blur30)" opacity="0.9"/>')

near = ridge(840, 80)
svg.append(poly(near, "#1A0F27"))
svg.append(f'<rect x="-50" y="800" width="2020" height="140" fill="url(#mistgrad)" filter="url(#blur30)" opacity="0.6"/>')

# Foreground cliff (right) where the figure stands
cliff = [(900, 1130), (980, 930), (1060, 890), (1160, 850), (1240, 830), (1300, 800),
         (1340, 792), (1420, 796), (1480, 820), (1560, 870), (1680, 900), (1800, 960), (1970, 980), (1970, 1130)]
svg.append('<polygon points="' + " ".join(f"{x},{y}" for x, y in cliff) + '" fill="#0B0612"/>')
# rim light on cliff edge
svg.append('<polyline points="' + " ".join(f"{x},{y}" for x, y in cliff[1:-1]) +
           f'" fill="none" stroke="{P["lavender"]}" stroke-opacity="0.35" stroke-width="2" filter="url(#softglow)"/>')

# Qi aura behind the figure
FX, FY = 1372, 792  # feet
svg.append(f'<ellipse cx="{FX}" cy="{FY - 120}" rx="190" ry="260" fill="url(#aura)"/>')

# Spiritual energy ribbons: tapered spirals rising around the figure
for i in range(9):
    side = -1 if i % 3 else 1
    x0 = FX + rng.uniform(-20, 20)
    y0 = FY - rng.uniform(10, 60)
    lift = rng.uniform(160, 420)
    reach = rng.uniform(260, 620) * side
    d = (f"M{x0:.0f},{y0:.0f} C{x0 + reach * 0.15:.0f},{y0 - lift * 0.5:.0f} "
         f"{x0 - reach * 0.55:.0f},{y0 - lift * 0.6:.0f} {x0 - reach:.0f},{y0 - lift:.0f}")
    w = rng.uniform(1.0, 2.6)
    for k, (sw, op) in enumerate(((w * 3.2, 0.10), (w * 1.6, 0.22), (w, 0.55))):
        svg.append(f'<path d="{d}" fill="none" stroke="{P["lavender"]}" stroke-width="{sw:.1f}" '
                   f'stroke-opacity="{op * rng.uniform(0.7, 1.1):.2f}" stroke-linecap="round" '
                   f'stroke-dasharray="{rng.uniform(300, 900):.0f} 2000"{" filter=%s" % chr(34) + "url(#glow)" + chr(34) if k == 2 else ""}/>')

# Cloaked cultivator silhouette, three-quarter back view, cape and long hair
# streaming left in the qi wind.
U = 1.0
def pt(dx, dy):
    return f"{FX + dx * U:.1f},{FY - dy * U:.1f}"
body = (
    f"M{pt(-14, 0)} L{pt(-10, 70)} "
    f"C{pt(-30, 90)} {pt(-80, 70)} {pt(-150, 40)} "          # robe hem flaring left
    f"C{pt(-118, 66)} {pt(-126, 84)} {pt(-176, 96)} "
    f"C{pt(-120, 118)} {pt(-80, 150)} {pt(-52, 186)} "
    f"C{pt(-100, 196)} {pt(-150, 206)} {pt(-214, 204)} "     # cape tip
    f"C{pt(-150, 226)} {pt(-80, 236)} {pt(-26, 232)} "
    f"C{pt(-22, 244)} {pt(-16, 250)} {pt(-10, 252)} "        # neck
    f"C{pt(-14, 266)} {pt(-6, 280)} {pt(6, 280)} "           # head
    f"C{pt(16, 280)} {pt(20, 266)} {pt(14, 252)} "
    f"C{pt(28, 246)} {pt(34, 232)} {pt(32, 214)} "           # right shoulder
    f"C{pt(30, 170)} {pt(24, 120)} {pt(22, 80)} "
    f"C{pt(26, 50)} {pt(30, 24)} {pt(24, 0)} Z"
)
svg.append(f'<path d="{body}" fill="none" stroke="{P["lavender"]}" stroke-width="5" stroke-opacity="0.5" filter="url(#softglow)"/>')
svg.append(f'<path d="{body}" fill="#07040B"/>')
# long hair: thin tapered strands from the head, streaming left
for i in range(9):
    y = 262 - i * 5
    dy = rng.uniform(-30, 40)
    L = rng.uniform(120, 230)
    d = (f"M{pt(0, y)} C{pt(-L * 0.3, y + 16 + dy * 0.2)} {pt(-L * 0.6, y - 10 + dy * 0.6)} {pt(-L, y - 6 + dy)}")
    svg.append(f'<path d="{d}" fill="none" stroke="#0A0610" stroke-width="{rng.uniform(1.5, 4):.1f}" stroke-linecap="round"/>')
    svg.append(f'<path d="{d}" fill="none" stroke="{P["silver"]}" stroke-width="0.8" stroke-opacity="{rng.uniform(0.15, 0.4):.2f}"/>')
# sword hilt over the shoulder
svg.append(f'<line x1="{FX + 26}" y1="{FY - 268}" x2="{FX - 20}" y2="{FY - 140}" stroke="#07040B" stroke-width="5"/>')
svg.append(f'<line x1="{FX + 22}" y1="{FY - 258}" x2="{FX + 30}" y2="{FY - 280}" stroke="{P["silver"]}" stroke-width="2.2" stroke-opacity="0.75"/>')

# Floating qi particles, denser near the figure
for _ in range(180):
    if rng.random() < 0.6:
        x, y = rng.gauss(FX - 150, 260), rng.gauss(FY - 200, 160)
    else:
        x, y = rng.uniform(500, 1920), rng.uniform(300, 1060)
    r = rng.uniform(0.8, 2.6)
    svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{P["lavender"]}" opacity="{rng.uniform(0.3, 0.9):.2f}" filter="url(#glow)"/>')

# Low foreground mist and final grade
svg.append(f'<rect x="-50" y="960" width="2020" height="160" fill="url(#mistgrad)" filter="url(#blur30)" opacity="0.7"/>')
svg.append('<rect width="1920" height="1080" fill="url(#leftveil)"/>')
svg.append('<rect width="1920" height="1080" fill="url(#vignette)"/>')
svg.append("</svg>")

OUT.parent.mkdir(parents=True, exist_ok=True)
svg_path = OUT.with_suffix(".svg")
svg_path.write_text("\n".join(svg))
subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(OUT), str(svg_path)], check=True)
svg_path.unlink()
print(f"wrote {OUT} ({W}x{H})")
