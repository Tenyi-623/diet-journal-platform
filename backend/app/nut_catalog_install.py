"""Add nut ingredients and breakfasts without overwriting existing administrator edits."""

from .nut_catalog import INGREDIENTS, VERSION, recipes
from .recipe_catalog_install import install_entries


def install(c):
    return install_entries(c, INGREDIENTS, recipes(), VERSION)


if __name__ == "__main__":
    import psycopg
    from psycopg.rows import dict_row
    from backend.config import settings

    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        print(install(connection))
