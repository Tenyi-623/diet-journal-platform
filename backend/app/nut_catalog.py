"""Authored nut breakfasts using state-matched entries in the existing food dataset."""

VERSION = "nuts-breakfast-v1"

# code, zh/en/ja names, allergen tags, estimated JPY per 100g.
# These are estimated ingredient costs, not observed retail prices.
INGREDIENTS = [
    ("05040", "无盐烘烤巴旦木（扁桃仁）", "Unsalted roasted almonds", "アーモンド・いり・無塩", ["nuts"], 240),
    ("05014", "烘烤核桃", "Roasted walnuts", "くるみ・いり", ["nuts"], 260),
]
LABELS = {
    "05040": ("巴旦木", "almonds", "アーモンド"),
    "05014": ("核桃", "walnuts", "くるみ"),
}

# Nut weights are edible kernel weights in the named processing state.
DEFINITIONS = [
    ("nuts-b001", "核桃苹果牛奶燕麦碗", "Walnut, apple & milk oats", "くるみ・りんご・ミルクのオーツ",
     "oats", {"05014": 15, "01004": 65, "13003": 220, "07148": 120}),
    ("nuts-b002", "巴旦木香蕉豆浆燕麦碗", "Almond, banana & soy milk oats", "アーモンド・バナナ・豆乳のオーツ",
     "oats", {"05040": 15, "01004": 65, "04052": 220, "07107": 100}),
    ("nuts-b003", "核桃草莓酸奶燕麦碗", "Walnut, strawberry & yogurt oats", "くるみ・いちご・ヨーグルトのオーツ",
     "oats", {"05014": 20, "01004": 60, "13025": 200, "07012": 100}),
    ("nuts-b004", "巴旦木猕猴桃酸奶燕麦碗", "Almond, kiwi & yogurt oats", "アーモンド・キウイ・ヨーグルトのオーツ",
     "oats", {"05040": 20, "01004": 60, "13025": 200, "07054": 100}),
    ("nuts-b005", "核桃南瓜豆腐糙米早餐", "Walnut, pumpkin & tofu brown rice", "くるみ・かぼちゃ・豆腐の玄米朝食",
     "plate", {"05014": 15, "01085": 180, "04032": 120, "06049": 100}),
    ("nuts-b006", "巴旦木毛豆红薯早餐", "Almond, edamame & sweet potato breakfast", "アーモンド・枝豆・さつまいもの朝食",
     "plate", {"05040": 15, "02007": 220, "06016": 80, "06065": 80, "04052": 150}),
]


def instructions(style, parts):
    from .seed import INGREDIENTS as BASE
    from .recipe_catalog import INGREDIENTS as EXTENDED
    names = {r[0]: r[1:4] for r in [*BASE, *EXTENDED, *INGREDIENTS]}
    lists = ["、".join(f"{names[c][i]} {grams}g" for c, grams in parts.items()) for i in range(3)]
    if style == "oats":
        actions = (
            "燕麦按干重称量，用列出的牛奶或豆浆加热泡软；未列奶或豆浆时使用饮用水。若有酸奶，待燕麦放至适口温度后再加入。水果洗净，取可食部分切块。",
            "Weigh oats dry and soften with the listed milk or soy milk, or drinking water if neither is listed. Add yogurt, if listed, after cooling to serving temperature. Wash fruit and cut its edible flesh.",
            "オーツは乾燥重量で量り、記載の牛乳・豆乳、なければ飲用水で柔らかくします。ヨーグルトは食べやすい温度になってから加えます。果物は洗い、可食部を切ります。",
        )
    else:
        actions = (
            "米饭、红薯、南瓜和毛豆按名称标注的熟重称量并温热；豆腐加热后装盘。黄瓜如有列出，洗净切块。豆浆如有列出，单独配饮。",
            "Weigh prepared rice, sweet potato, pumpkin and edamame in their named cooked states and warm them. Heat tofu before plating. Wash and cut cucumber if listed; serve soy milk separately if listed.",
            "ごはん・さつまいも・かぼちゃ・枝豆は名称に記載した調理済み重量で量り、温めます。豆腐は加熱して盛ります。きゅうりは洗って切り、豆乳は別に添えます。",
        )
    return {
        "zh": f"1. 基准份量用料：{lists[0]}。\n2. {actions[0]}\n"
              "3. 坚果按列出的烘烤状态及去壳可食重量称量，切碎后加入燕麦或撒在餐盘上。不另加盐、糖、油或未列出的配料。\n"
              "4. 本配方含坚果；购买时核对配料和加工状态。调整份量后，各食材克数以页面清单为准。",
        "en": f"1. Base serving ingredients: {lists[1]}.\n2. {actions[1]}\n"
              "3. Weigh edible nut kernels in the listed roasted state, chop and add to the oats or plate. Do not add salt, sugar, oil or unlisted ingredients.\n"
              "4. This recipe contains nuts; check ingredient labels and processing state. For scaled servings, use the weights shown on the page.",
        "ja": f"1. 基準量の材料：{lists[2]}。\n2. {actions[2]}\n"
              "3. ナッツは記載のいり状態で殻を除いた可食部を量り、刻んでオーツや料理に加えます。塩・砂糖・油・記載のない材料は追加しません。\n"
              "4. このレシピはナッツを含みます。原材料表示と加工状態を確認してください。量を変更した場合は画面の材料一覧の重量を使用してください。",
    }


def recipes():
    return [
        {
            "id": rid, "version": VERSION, "meal": "breakfast",
            "name": {"zh": zh, "en": en, "ja": ja},
            "ingredients": dict(parts),
            "data": {
                "image": f"/api/recipe-images/{rid}",
                "image_kind": "original_svg_illustration", "art": style,
                "minutes": 15 if style == "oats" else 20,
                "scales": [0.8, 1.0, 1.2, 1.4],
                "instructions": instructions(style, parts),
                "review": "authored_recipe_not_dietitian_reviewed",
                "recipe_source": "application_authored", "catalog_version": VERSION,
                "search_keywords": ["坚果", "nuts", "ナッツ"],
                "purchase_cost_available": False,
                "nutrition_method": "sum_of_ingredients_in_named_state",
            },
        }
        for rid, zh, en, ja, style, parts in DEFINITIONS
    ]
