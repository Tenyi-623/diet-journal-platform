"""Original deterministic SVG food illustrations, not photographs or exact portion depictions."""

from pathlib import Path
from html import escape
from backend.app.seed import RECIPES

root = Path(__file__).resolve().parents[1] / "frontend/public/recipe-art"
root.mkdir(parents=True, exist_ok=True)
for i, (rid, meal, zh, en, ja, parts, kind) in enumerate(RECIPES):
    bg = ["#eee5d7", "#e7ecdf", "#eadfce", "#f0e6da"][i % 4]
    if kind == "salmon":
        main = '<g transform="rotate(-18 260 230)"><rect x="180" y="160" width="170" height="120" rx="45" fill="#e59b78"/><path d="M207 169l90 100M240 160l87 95M273 167l66 70" stroke="#f8c7a6" stroke-width="13" stroke-linecap="round"/></g>'
    elif kind == "chicken":
        main = '<g transform="rotate(-18 260 230)"><ellipse cx="270" cy="225" rx="100" ry="68" fill="#d9b17d"/><path d="M210 183l40 106M247 166l45 120M289 170l40 97" stroke="#a87145" stroke-width="7" opacity=".6"/></g>'
    elif kind == "tofu":
        main = "".join(
            f'<rect x="{x}" y="{y}" width="65" height="53" rx="9" fill="#f8edcf" stroke="#dbcda7" stroke-width="2" transform="rotate(-12 {x} {y})"/>'
            for x, y in [(175, 175), (245, 165), (205, 232), (275, 225)]
        )
    elif kind == "egg":
        main = '<ellipse cx="245" cy="223" rx="98" ry="64" fill="#fff9e6" transform="rotate(-20 245 223)"/><circle cx="245" cy="218" r="35" fill="#e4b545"/>'
    else:
        main = (
            '<ellipse cx="290" cy="210" rx="117" ry="95" fill="#d9c6a5"/>'
            + "".join(
                f'<ellipse cx="{205 + (j * 37) % 160}" cy="{153 + (j * 23) % 100}" rx="10" ry="5" fill="#efe0c5" transform="rotate({j * 13} 280 210)"/>'
                for j in range(35)
            )
            + '<g fill="#f8e7ad" stroke="#d6bd7e" stroke-width="3"><circle cx="260" cy="182" r="24"/><circle cx="308" cy="171" r="24"/><circle cx="346" cy="199" r="24"/></g>'
        )
    veg = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>'
        for x, y, r, c in [
            (400, 168, 34, "#476b3a"),
            (425, 211, 36, "#587c43"),
            (390, 240, 32, "#63834b"),
            (378, 193, 26, "#375e37"),
            (414, 169, 18, "#75964d"),
        ]
    )
    if kind == "oats":
        veg = '<g fill="#ae5550"><circle cx="372" cy="241" r="20"/><circle cx="354" cy="263" r="15"/></g><path d="M372 220q23-29 44-20q-12 32-44 20" fill="#52744d"/>'
    rice = (
        '<ellipse cx="260" cy="295" rx="105" ry="48" fill="#f5efdf"/>'
        if kind != "oats"
        else ""
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="440" viewBox="0 0 640 440" role="img" aria-label="{escape(en, quote=True)}: illustration">
<defs><filter id="shadow"><feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#5e513b" flood-opacity=".16"/></filter><pattern id="cloth" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 0H12M0 0V12" stroke="#fff" opacity=".16"/></pattern></defs>
<rect width="640" height="440" fill="{bg}"/><rect width="640" height="440" fill="url(#cloth)"/><path d="M510 0L640 50v350l-88 40z" fill="#b9c1a6" opacity=".3"/>
<g filter="url(#shadow)"><ellipse cx="310" cy="230" rx="217" ry="173" fill="#fcfbf4"/><ellipse cx="310" cy="226" rx="186" ry="143" fill="#f1eee4"/>{rice}{main}{veg}<g fill="#cb7550"><ellipse cx="365" cy="300" rx="27" ry="12" transform="rotate(23 365 300)"/><ellipse cx="403" cy="288" rx="23" ry="11" transform="rotate(-20 403 288)"/></g></g>
<g stroke="#a38766" stroke-width="7" stroke-linecap="round"><path d="M550 90l-7 260M570 90l-9 260"/></g></svg>'''
    (root / f"{rid}.svg").write_text(svg)
print("20 original recipe illustration assets written.")
