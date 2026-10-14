"""Reviewed-by-engineering demo templates; prices are synthetic, NOT retail observations."""

from psycopg.types.json import Jsonb
from backend.knowledge import connect

VERSION = "demo-v1"
# Costs are per 100g of the edible, prepared state: no fictitious raw-to-cooked conversion.
INGREDIENTS = [
    ("01088", "米饭", "Rice", "ごはん", [], 40),
    ("01085", "糙米饭", "Brown rice", "玄米ごはん", [], 45),
    ("01004", "燕麦片（干）", "Dry oats", "オートミール", [], 65),
    ("04032", "木棉豆腐", "Firm tofu", "木綿豆腐", ["soy"], 38),
    ("13003", "牛奶", "Milk", "牛乳", ["milk"], 28),
    ("12005", "水煮蛋", "Boiled egg", "ゆで卵", ["egg"], 70),
    ("11288", "烤鸡胸（去皮）", "Grilled chicken", "鶏むね肉・焼き", [], 150),
    ("10136", "烤鲑鱼", "Grilled salmon", "しろさけ・焼き", ["fish"], 280),
    ("06264", "水煮西兰花", "Boiled broccoli", "ブロッコリー・ゆで", [], 80),
    ("06215", "水煮胡萝卜", "Boiled carrot", "にんじん・ゆで", [], 38),
    ("06268", "水煮菠菜", "Boiled spinach", "ほうれんそう・ゆで", [], 90),
    ("06182", "番茄", "Tomato", "トマト", [], 65),
    ("06062", "水煮卷心菜", "Boiled cabbage", "キャベツ・ゆで", [], 35),
    ("07107", "香蕉（可食部）", "Banana", "バナナ", [], 40),
    ("07148", "苹果（去皮）", "Peeled apple", "りんご・皮なし", [], 65),
    ("14001", "橄榄油", "Olive oil", "オリーブ油", [], 180),
    ("13025", "原味无糖酸奶", "Plain yogurt", "プレーンヨーグルト", ["milk"], 40),
    ("02007", "蒸红薯", "Steamed sweet potato", "さつまいも・蒸し", [], 55),
    ("17007", "酱油", "Soy sauce", "こいくちしょうゆ", ["soy", "wheat"], 30),
]
RECIPES = [
    (
        "b1",
        "breakfast",
        "香蕉燕麦早餐",
        "Banana oat breakfast",
        "バナナとオートミール",
        {"01004": 65, "13003": 200, "07107": 100, "12005": 50},
        "oats",
    ),
    (
        "b2",
        "breakfast",
        "酸奶苹果燕麦",
        "Apple yogurt oats",
        "りんごヨーグルトオーツ",
        {"01004": 70, "13025": 200, "07148": 120, "12005": 50},
        "oats",
    ),
    (
        "b3",
        "breakfast",
        "豆腐蔬菜饭早餐",
        "Tofu rice breakfast",
        "豆腐と野菜の朝ごはん",
        {"01088": 220, "04032": 150, "06264": 80, "14001": 8, "17007": 4},
        "tofu",
    ),
    (
        "b4",
        "breakfast",
        "红薯鸡蛋早餐",
        "Sweet potato & eggs",
        "さつまいもと卵",
        {"02007": 250, "12005": 100, "13003": 150},
        "egg",
    ),
    (
        "b5",
        "breakfast",
        "糙米鸡蛋蔬菜碗",
        "Brown rice egg bowl",
        "玄米と卵のボウル",
        {"01085": 230, "12005": 100, "06182": 120, "14001": 5},
        "egg",
    ),
    (
        "b6",
        "breakfast",
        "香蕉豆腐燕麦碗",
        "Banana tofu oats",
        "バナナ豆腐オーツ",
        {"01004": 75, "04032": 180, "07107": 120},
        "oats",
    ),
    (
        "l1",
        "lunch",
        "烤鸡西兰花米饭",
        "Chicken broccoli plate",
        "鶏肉とブロッコリー定食",
        {"01088": 230, "11288": 100, "06264": 120, "06215": 80, "14001": 8, "17007": 5},
        "chicken",
    ),
    (
        "l2",
        "lunch",
        "鲑鱼糙米饭",
        "Salmon brown rice",
        "鮭と玄米定食",
        {"01085": 250, "10136": 100, "06268": 100, "06215": 70, "14001": 7, "17007": 4},
        "salmon",
    ),
    (
        "l3",
        "lunch",
        "豆腐时蔬米饭",
        "Tofu vegetable plate",
        "豆腐と彩り野菜定食",
        {
            "01088": 250,
            "04032": 250,
            "06264": 120,
            "06215": 80,
            "14001": 10,
            "17007": 5,
        },
        "tofu",
    ),
    (
        "l4",
        "lunch",
        "鸡蛋番茄糙米饭",
        "Egg tomato rice",
        "卵とトマトの玄米定食",
        {
            "01085": 240,
            "12005": 100,
            "06182": 160,
            "06062": 100,
            "14001": 10,
            "17007": 4,
        },
        "egg",
    ),
    (
        "l5",
        "lunch",
        "烤鸡红薯餐",
        "Chicken sweet potato",
        "鶏肉とさつまいも",
        {"02007": 300, "11288": 100, "06264": 100, "14001": 8, "17007": 5},
        "chicken",
    ),
    (
        "l6",
        "lunch",
        "鲑鱼蔬菜米饭",
        "Salmon vegetable plate",
        "鮭と野菜のごはん",
        {
            "01088": 240,
            "10136": 110,
            "06062": 150,
            "06182": 100,
            "14001": 8,
            "17007": 4,
        },
        "salmon",
    ),
    (
        "l7",
        "lunch",
        "豆腐鸡蛋饭",
        "Tofu egg rice",
        "豆腐と卵のごはん",
        {"01088": 230, "04032": 150, "12005": 70, "06268": 100, "14001": 8, "17007": 5},
        "tofu",
    ),
    (
        "d1",
        "dinner",
        "鸡肉菠菜糙米饭",
        "Chicken spinach rice",
        "鶏肉とほうれんそうの玄米",
        {
            "01085": 230,
            "11288": 100,
            "06268": 120,
            "06215": 80,
            "14001": 10,
            "17007": 5,
        },
        "chicken",
    ),
    (
        "d2",
        "dinner",
        "鲑鱼西兰花晚餐",
        "Salmon broccoli dinner",
        "鮭とブロッコリーの夕食",
        {"01088": 240, "10136": 110, "06264": 150, "14001": 8, "17007": 5},
        "salmon",
    ),
    (
        "d3",
        "dinner",
        "豆腐卷心菜饭",
        "Tofu cabbage rice",
        "豆腐とキャベツのごはん",
        {
            "01085": 240,
            "04032": 250,
            "06062": 150,
            "06215": 100,
            "14001": 10,
            "17007": 5,
        },
        "tofu",
    ),
    (
        "d4",
        "dinner",
        "鸡蛋红薯蔬菜餐",
        "Egg sweet potato plate",
        "卵とさつまいもの夕食",
        {"02007": 300, "12005": 100, "06264": 100, "13025": 100, "14001": 5},
        "egg",
    ),
    (
        "d5",
        "dinner",
        "烤鸡番茄米饭",
        "Chicken tomato rice",
        "鶏肉とトマトのごはん",
        {
            "01088": 230,
            "11288": 100,
            "06182": 160,
            "06062": 120,
            "14001": 10,
            "17007": 5,
        },
        "chicken",
    ),
    (
        "d6",
        "dinner",
        "鲑鱼豆腐糙米饭",
        "Salmon tofu brown rice",
        "鮭と豆腐の玄米定食",
        {"01085": 220, "10136": 80, "04032": 120, "06268": 100, "14001": 8, "17007": 4},
        "salmon",
    ),
    (
        "d7",
        "dinner",
        "双蔬豆腐碗",
        "Garden tofu bowl",
        "彩り野菜と豆腐ボウル",
        {
            "01088": 250,
            "04032": 250,
            "06264": 120,
            "06182": 120,
            "14001": 10,
            "17007": 5,
        },
        "tofu",
    ),
]


def seed():
    with connect() as c:
        for code, zh, en, ja, allergens, price in INGREDIENTS:
            c.execute(
                """INSERT INTO app_ingredients VALUES(%s,1,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (
                    code,
                    Jsonb({"zh": zh, "en": en, "ja": ja}),
                    allergens,
                    price,
                    Jsonb(
                        {
                            "version": VERSION,
                            "state": "as_named_edible",
                            "price_kind": "synthetic_demo",
                            "price_basis": "JPY per 100g edible prepared ingredient",
                            "cross_contact": "unknown",
                            "review": "engineering_checked_not_clinical",
                        }
                    ),
                ),
            )
        for rid, meal, zh, en, ja, parts, art in RECIPES:
            data = {
                "image": f"/api/recipe-images/{rid}",
                "image_kind": "original_svg_illustration",
                "art": art,
                "minutes": 15 if meal == "breakfast" else 30,
                "scales": [0.8, 1.0, 1.2, 1.4],
                "instructions": {
                    "zh": "按列示的可食重量称量。熟米饭、烤肉/鱼和煮蔬菜均按熟重；水果去皮。燕麦用列出的牛奶或适量饮用水泡软。将已熟食材与即食配料装盘，按配方加入油和酱油；不另加盐。肉、鱼和蛋须先充分做熟，切勿把熟重当原料采购重量。",
                    "en": "Weigh edible portions as listed. Rice, grilled meat/fish and boiled vegetables use cooked weights. Peel fruit; soften oats with the listed milk or drinking water. Assemble fully cooked ingredients; add only the listed oil and sauce, with no extra salt. Cook meat, fish and eggs thoroughly before weighing.",
                    "ja": "表示の可食重量で計量します。ごはん・肉・魚・ゆで野菜は調理後重量です。果物は皮を除き、オーツは表示の牛乳または飲用水で戻します。十分に加熱済みの材料を盛り、記載の油・しょうゆのみを加えます。追加の塩は使いません。",
                },
                "review": "demo_template_not_dietitian_reviewed",
                "purchase_cost_available": False,
            }
            c.execute(
                "INSERT INTO app_recipes(id,version,meal,name,ingredients,data) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    rid,
                    VERSION,
                    meal,
                    Jsonb({"zh": zh, "en": en, "ja": ja}),
                    Jsonb(parts),
                    Jsonb(data),
                ),
            )
        for i, budget in enumerate([900, 1100, 1300, 1500, 1700, 1900], 1):
            c.execute(
                "INSERT INTO app_income_policies VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    f"JPY_A{i}",
                    VERSION,
                    (i - 1) * 2000000,
                    i * 2000000 if i < 6 else None,
                    budget,
                    f"{(i - 1) * 200}–{i * 200}万円" if i < 6 else "1000万円以上",
                    Jsonb(
                        {
                            "basis": "personal_pretax_annual_JPY",
                            "status": "demo_only",
                            "explanation": "Synthetic test budgets calibrated to demo recipe cost range; not disposable income estimates or official income classes.",
                        }
                    ),
                ),
            )
        from .recipe_catalog_install import install

        install(c)
        from .nut_catalog_install import install as install_nuts

        install_nuts(c)
    print(
        "Seeded 49 ingredients, 184 recipes and 6 income policies; existing data unchanged."
    )


if __name__ == "__main__":
    seed()
