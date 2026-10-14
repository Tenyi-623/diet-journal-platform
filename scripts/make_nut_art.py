"""Generate only the six new nut-breakfast illustrations in three languages."""

from backend.app.nut_catalog import recipes, LABELS as NUT_LABELS
from backend.app.recipe_catalog import LABELS
from scripts.make_catalog_art import ART, illustration


def main():
    ART.mkdir(parents=True, exist_ok=True)
    for row in recipes():
        for language in ("zh", "en", "ja"):
            suffix = ".svg" if language == "zh" else f".{language}.svg"
            (ART / (row["id"] + suffix)).write_text(
                illustration(row, language, labels={**LABELS, **NUT_LABELS})
            )
    print("Generated 6 nut-breakfast illustrations in three languages.")


if __name__ == "__main__":
    main()
