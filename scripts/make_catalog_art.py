"""Generate ingredient-specific SVG illustrations without changing existing art."""

from html import escape
from pathlib import Path

from backend.app.recipe_catalog import LABELS, recipes

ART = Path(__file__).resolve().parents[1] / "frontend/public/recipe-art"
COLORS = {
    "01088": "#eee3c8", "01085": "#c6a578", "01004": "#d1b689",
    "01039": "#ead4a1", "01063": "#dfbd6d", "01026": "#bc824a",
    "02019": "#e7d291", "02007": "#dab66f", "04032": "#eee7cf",
    "11288": "#bf8c61", "11229": "#d9bc98", "11278": "#ad806e",
    "10136": "#da9778", "10156": "#8c9b9b", "10206": "#e1dcca",
    "12005": "#e2b539", "04066": "#c7ab65", "04094": "#8e9471",
    "04046": "#aa9161", "06016": "#829b59", "06182": "#cb7963",
    "06247": "#bd7257", "06215": "#d79855", "06049": "#dcb05a",
    "06176": "#debf58", "08017": "#a7927e", "08040": "#8a7460",
    "07107": "#e6cf7f", "07148": "#dfbba0", "07012": "#c37671",
    "07054": "#95a25a", "07040": "#dbab5e", "13025": "#f6f0de",
    "13003": "#f3ecda", "04052": "#e7d8b9",
    "05040": "#b97f4a", "05014": "#aa7952",
}


def illustration(row, lang="zh", labels=None):
    labels = LABELS if labels is None else labels
    index = ("zh", "en", "ja").index(lang)
    caption = ("食材示意图", "Ingredient illustration", "食材イメージ")[index]
    style = row["data"]["art"]
    parts = [(c, g) for c, g in row["ingredients"].items() if c in labels]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="480" viewBox="0 0 720 480" role="img">',
        f"<title>{escape(row['name'][lang])} · {caption}</title>",
        '<defs><filter id="s" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0" dy="9" stdDeviation="9" flood-color="#594b32" flood-opacity=".13"/>'
        '</filter></defs>',
        '<rect width="720" height="480" fill="#f0ecdf"/>',
        '<path d="M550 0h170v480H660z" fill="#e6e3d6"/>',
        '<ellipse cx="344" cy="238" rx="231" ry="182" fill="#fffcf3" filter="url(#s)"/>',
        '<ellipse cx="344" cy="238" rx="201" ry="152" fill="#ede9dc"/>',
    ]
    if style in ("oats", "soup"):
        svg.append('<ellipse cx="344" cy="238" rx="187" ry="140" fill="#d9c59d"/>')
    # Distinct visual ingredients occupy fixed sectors. Titles and small tags
    # identify the illustration as a schematic, never a real photograph.
    centers = [(265, 195), (410, 205), (285, 292), (421, 292), (351, 140), (350, 345)]
    for n, (code, grams) in enumerate(parts[:6]):
        x, y = centers[n]
        color = COLORS.get(code, "#819268")
        if code in ("01063", "01039"):
            for j in range(8):
                svg.append(f'<path d="M{x-53} {y-30+j*8}q45 -35 90 0t-70 15" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
        elif code == "01026":
            svg.append(f'<rect x="{x-55}" y="{y-45}" width="110" height="90" rx="19" fill="{color}"/>')
            svg.append(f'<rect x="{x-45}" y="{y-35}" width="90" height="70" rx="15" fill="#e8d4a7"/>')
        elif code == "12005":
            svg.append(f'<ellipse cx="{x}" cy="{y}" rx="53" ry="35" fill="#fff8df"/><circle cx="{x}" cy="{y}" r="22" fill="{color}"/>')
        elif code in ("05040", "05014"):
            for j in range(7):
                dx, dy = (j * 29) % 82 - 38, (j * 19) % 54 - 25
                width = 12 if code == "05040" else 17
                svg.append(f'<ellipse cx="{x+dx}" cy="{y+dy}" rx="{width}" ry="19" fill="{color}" stroke="#89623f" stroke-width="2" transform="rotate(-25 {x+dx} {y+dy})"/>')
                svg.append(f'<path d="M{x+dx} {y+dy-13}q-6 12 0 26" fill="none" stroke="#e5bf8f" stroke-width="2"/>')
        elif code in ("11288", "11229", "11278", "10136", "10156", "10206"):
            svg.append(f'<rect x="{x-54}" y="{y-30}" width="108" height="60" rx="23" fill="{color}" transform="rotate(-12 {x} {y})"/>')
            for j in range(4):
                svg.append(f'<path d="M{x-30+j*19} {y-22}l18 39" stroke="#ffffff" opacity=".3" stroke-width="5"/>')
        else:
            for j in range(7):
                dx, dy = (j * 29) % 82 - 38, (j * 19) % 54 - 25
                svg.append(f'<ellipse cx="{x+dx}" cy="{y+dy}" rx="22" ry="16" fill="{color}" stroke="#fff" stroke-opacity=".18" stroke-width="2"/>')
    svg.extend([
        '<path d="M603 112l-9 244M622 112l-9 244" stroke="#9f8666" stroke-width="6" stroke-linecap="round"/>',
        '<rect x="30" y="24" width="192" height="32" rx="16" fill="#fcfaf3"/>',
        f'<text x="126" y="46" text-anchor="middle" font-size="15" font-family="sans-serif" fill="#786e58">{caption}</text>',
    ])
    for n, (code, _) in enumerate(parts[:4]):
        x = 105 + n * 165
        svg.append(f'<text x="{x}" y="447" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#726b59">{escape(labels[code][index])}</text>')
    return "".join(svg) + "</svg>"


def main():
    ART.mkdir(parents=True, exist_ok=True)
    for row in recipes():
        (ART / f"{row['id']}.svg").write_text(illustration(row))
        for lang in ("en", "ja"):
            (ART / f"{row['id']}.{lang}.svg").write_text(illustration(row, lang))
    print("Generated 158 catalog illustrations in three languages; original recipe art unchanged.")


if __name__ == "__main__":
    main()
