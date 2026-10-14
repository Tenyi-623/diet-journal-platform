"""Versioned, authored meal compositions using existing MEXT food identifiers.

These are application recipes, not recipes quoted from the nutrition source.
Prices remain explicit estimates. Nutrition is calculated by the existing planner.
"""

VERSION = "catalog-178-v1.1"

# code, Chinese, English, Japanese, allergens, estimated JPY/100g.
# State in the name is also the weighing state; cooked foods use cooked weights.
INGREDIENTS = [
    ("01039", "煮乌冬面", "Cooked udon", "うどん・ゆで", ["wheat"], 35),
    ("01063", "意大利面（干）", "Dry pasta", "パスタ・乾", ["wheat"], 60),
    ("01026", "切片面包", "Sliced bread", "食パン", ["wheat", "milk", "egg", "soy"], 65),
    ("02019", "水煮去皮土豆", "Boiled peeled potato", "じゃがいも・皮なし・水煮", [], 35),
    ("06049", "水煮南瓜", "Boiled pumpkin", "西洋かぼちゃ・ゆで", [], 50),
    ("06087", "水煮小松菜", "Boiled komatsuna", "こまつな・ゆで", [], 65),
    ("06161", "水煮青梗菜", "Boiled bok choy", "チンゲンサイ・ゆで", [], 50),
    ("06008", "水煮芦笋", "Boiled asparagus", "アスパラガス・ゆで", [], 130),
    ("06055", "水煮菜花", "Boiled cauliflower", "カリフラワー・ゆで", [], 85),
    ("06011", "水煮四季豆", "Boiled green beans", "さやいんげん・ゆで", [], 85),
    ("06176", "水煮甜玉米粒", "Boiled sweet corn", "スイートコーン・ゆで", [], 60),
    ("06065", "黄瓜", "Cucumber", "きゅうり・生", [], 45),
    ("06247", "红甜椒（生）", "Raw red pepper", "赤ピーマン・生", [], 95),
    ("08017", "水煮蟹味菇", "Boiled shimeji", "ぶなしめじ・ゆで", [], 80),
    ("08040", "水煮鲜香菇", "Boiled shiitake", "生しいたけ・菌床栽培・ゆで", [], 100),
    ("06016", "水煮毛豆仁", "Boiled shelled edamame", "えだまめ・ゆで", ["soy"], 85),
    ("04066", "水煮鹰嘴豆", "Boiled chickpeas", "ひよこまめ・ゆで", [], 60),
    ("04094", "水煮扁豆", "Boiled lentils", "レンズまめ・ゆで", [], 60),
    ("04046", "纳豆（不含料包）", "Natto without sauce", "糸引き納豆・たれなし", ["soy"], 60),
    ("04052", "无调味豆浆", "Plain soy milk", "無調整豆乳", ["soy"], 30),
    ("07054", "绿心猕猴桃（可食部）", "Peeled green kiwi", "緑肉キウイ・可食部", [], 100),
    ("07012", "草莓（可食部）", "Hulled strawberries", "いちご・可食部", [], 150),
    ("07040", "脐橙果肉", "Navel orange flesh", "ネーブルオレンジ・砂じょう", [], 75),
    ("10156", "烤鲭鱼（未盐渍）", "Grilled unsalted mackerel", "まさば・焼き", ["fish"], 180),
    ("10206", "烤鳕鱼（未盐渍）", "Grilled unsalted cod", "まだら・焼き", ["fish"], 230),
    ("11278", "烤猪里脊", "Grilled pork tenderloin", "豚ヒレ・赤肉・焼き", [], 180),
    ("11229", "水煮鸡里脊", "Boiled chicken tenderloin", "鶏ささみ・ゆで", [], 140),
    ("07156", "鲜柠檬汁", "Fresh lemon juice", "レモン果汁", [], 100),
]

# Short names are editorial names for composing titles, not replacements for the
# full state-qualified ingredient labels displayed in recipe details.
LABELS = {
    "01088": ("米饭", "rice", "ごはん"),
    "01085": ("糙米饭", "brown rice", "玄米ごはん"),
    "01004": ("燕麦", "oats", "オーツ"),
    "01039": ("乌冬面", "udon", "うどん"),
    "01063": ("意面", "pasta", "パスタ"),
    "01026": ("面包", "bread", "パン"),
    "02019": ("土豆", "potato", "じゃがいも"),
    "02007": ("红薯", "sweet potato", "さつまいも"),
    "04032": ("豆腐", "tofu", "豆腐"),
    "04066": ("鹰嘴豆", "chickpea", "ひよこ豆"),
    "04094": ("扁豆", "lentil", "レンズ豆"),
    "04046": ("纳豆", "natto", "納豆"),
    "04052": ("豆浆", "soy milk", "豆乳"),
    "06016": ("毛豆", "edamame", "枝豆"),
    "12005": ("鸡蛋", "egg", "卵"),
    "11288": ("烤鸡胸", "grilled chicken", "焼き鶏むね"),
    "11229": ("鸡丝", "shredded chicken", "ささみ"),
    "11278": ("猪里脊", "pork tenderloin", "豚ヒレ"),
    "10136": ("鲑鱼", "salmon", "鮭"),
    "10156": ("鲭鱼", "mackerel", "さば"),
    "10206": ("鳕鱼", "cod", "たら"),
    "06264": ("西兰花", "broccoli", "ブロッコリー"),
    "06215": ("胡萝卜", "carrot", "にんじん"),
    "06268": ("菠菜", "spinach", "ほうれんそう"),
    "06182": ("番茄", "tomato", "トマト"),
    "06062": ("卷心菜", "cabbage", "キャベツ"),
    "06049": ("南瓜", "pumpkin", "かぼちゃ"),
    "06087": ("小松菜", "komatsuna", "小松菜"),
    "06161": ("青梗菜", "bok choy", "チンゲンサイ"),
    "06008": ("芦笋", "asparagus", "アスパラガス"),
    "06055": ("菜花", "cauliflower", "カリフラワー"),
    "06011": ("四季豆", "green bean", "いんげん"),
    "06176": ("玉米", "corn", "コーン"),
    "06065": ("黄瓜", "cucumber", "きゅうり"),
    "06247": ("甜椒", "red pepper", "パプリカ"),
    "08017": ("蟹味菇", "shimeji", "しめじ"),
    "08040": ("香菇", "shiitake", "しいたけ"),
    "07107": ("香蕉", "banana", "バナナ"),
    "07148": ("苹果", "apple", "りんご"),
    "07054": ("猕猴桃", "kiwi", "キウイ"),
    "07012": ("草莓", "strawberry", "いちご"),
    "07040": ("脐橙", "orange", "オレンジ"),
    "13003": ("牛奶", "milk", "ミルク"),
    "13025": ("酸奶", "yogurt", "ヨーグルト"),
}

# Authored combinations, not a Cartesian-product generator. Each line is a
# distinct composition with explicit amounts. Breakfast format:
# style | title ingredient IDs | all ingredients in grams.
BREAKFAST = """
oats|07012 13003 01004|01004:70 13003:220 07012:120 12005:50
oats|07054 13025 01004|01004:70 13025:200 07054:100 12005:50
oats|07040 04052 01004|01004:75 04052:220 07040:120 12005:50
oats|07148 13003 01004|01004:70 13003:220 07148:120 04032:80
oats|07107 04052 01004|01004:75 04052:220 07107:100 12005:50
oats|07012 13025 01004|01004:75 13025:200 07012:120 07107:60
oats|06049 13003 01004|01004:70 13003:200 06049:100 12005:50
oats|02007 04052 01004|01004:60 04052:220 02007:100 12005:50
oats|06176 12005 01004|01004:70 06176:80 12005:100 06268:60 14001:4
oats|08040 04032 01004|01004:75 04032:180 08040:70 06161:80 14001:5 17007:3
oats|11229 06049 01004|01004:75 11229:70 06049:100 06087:60 14001:5
oats|04094 06182 01004|01004:65 04094:120 06182:100 06268:60 14001:5
toast|12005 06065 01026|01026:100 12005:100 06065:80 13003:180
toast|04066 06182 01026|01026:100 04066:100 06182:100 13025:150 14001:4
toast|11229 06247 01026|01026:100 11229:70 06247:70 13003:180 14001:4
toast|04032 06016 01026|01026:100 04032:100 06016:60 06182:80 04052:150
toast|12005 06049 01026|01026:100 12005:50 06049:100 13025:180
toast|07107 13025 01026|01026:100 07107:100 13025:180 12005:50
toast|07012 13025 01026|01026:100 07012:120 13025:180 12005:50
toast|04094 08017 01026|01026:100 04094:120 08017:60 06182:80 14001:5
plate|04046 06087 01085|01085:210 04046:50 06087:80 12005:50 14001:4
plate|06016 12005 01088|01088:200 06016:80 12005:50 06182:100 14001:4
plate|10206 06049 01085|01085:210 10206:70 06049:100 06065:60 14001:5
plate|04066 06161 01088|01088:210 04066:100 06161:100 14001:5 17007:3
plate|11229 08040 01085|01085:210 11229:70 08040:80 06176:60 14001:5
plate|04032 06176 01088|01088:210 04032:150 06176:70 06087:80 14001:4
plate|10156 06182 01085|01085:200 10156:60 06182:100 06065:70 07156:8
plate|04094 06049 01088|01088:200 04094:100 06049:100 06268:60 14001:4
plate|12005 06008 02019|02019:250 12005:100 06008:80 13003:180 14001:5
plate|04032 06176 02019|02019:250 04032:150 06176:80 04052:180 14001:5
plate|11229 06182 02019|02019:250 11229:80 06182:100 13025:180 14001:5
plate|04066 06065 02019|02019:250 04066:100 06065:80 13003:180 14001:5
plate|07054 13025 02007|02007:250 13025:180 07054:100 12005:50
plate|07040 04052 02007|02007:250 04052:220 07040:100 12005:50
plate|04032 06049 02007|02007:230 04032:150 06049:80 13003:150
plate|06016 12005 02007|02007:230 06016:80 12005:50 06182:100
soup|12005 08017 01088|01088:220 12005:100 08017:80 06161:80 14001:5 17007:3
soup|11229 06049 01088|01088:220 11229:80 06049:100 06268:70 14001:5
soup|04032 06176 01085|01085:220 04032:150 06176:80 06087:70 14001:4
soup|04094 06182 01085|01085:210 04094:120 06182:100 06215:70 14001:5
soup|10206 06161 01088|01088:230 10206:80 06161:100 06049:80 14001:5
soup|04066 06055 01085|01085:210 04066:120 06055:100 06215:60 14001:5
"""

# Main meals: style | staple | protein | vegetable 1 | vegetable 2 | dressing.
# Quantities vary by food/state in PORTIONS; recipes have distinct ingredient
# sets, rather than being duplicated just to change their meal slot or name.
LUNCH = """
plate 01085 11288 06008 06049 lemon
plate 01088 11288 08040 06161 soy
plate 01085 11229 06065 06176 lemon
plate 01088 11229 06087 08017 soy
plate 01085 11278 06264 06247 lemon
plate 01088 11278 06011 06215 soy
plate 01085 10136 06008 06182 lemon
plate 01088 10136 06055 06049 lemon
plate 01085 10156 06065 06182 lemon
plate 01088 10156 06161 08040 soy
plate 01085 10206 06049 06087 lemon
plate 01088 10206 06264 06176 lemon
plate 01085 04032 08040 06161 soy
plate 01088 04032 06008 06247 lemon
plate 01085 12005 06011 08017 soy
plate 01088 12005 06049 06087 lemon
plate 01085 04066 06182 06065 lemon
plate 01088 04066 06055 06215 lemon
plate 01085 04094 08040 06087 soy
plate 01088 04094 06049 06182 lemon
plate 01085 06016 06264 06176 lemon
plate 01088 06016 06161 08017 soy
plate 01085 04046 06087 06049 soy
plate 01088 04046 06065 06182 lemon
plate 02007 11278 06011 06055 lemon
plate 02007 10206 06087 06176 lemon
plate 02007 04032 06008 08040 soy
plate 02007 04066 06065 06247 lemon
salad 02019 11229 06065 06182 lemon
salad 02019 10136 06008 06176 lemon
salad 02019 12005 06011 06247 lemon
salad 02019 04066 06065 06049 lemon
salad 02019 04094 06182 06055 lemon
salad 01085 11229 06065 06247 lemon
salad 01085 04066 06176 06008 lemon
salad 01088 04032 06065 06182 lemon
pasta 01063 11229 06182 06268 lemon
pasta 01063 10136 06008 08017 lemon
pasta 01063 10206 06055 06182 lemon
pasta 01063 11278 08040 06087 soy
pasta 01063 04032 08017 06161 soy
pasta 01063 04066 06182 06049 lemon
pasta 01063 04094 06215 06087 lemon
pasta 01063 12005 06264 06176 lemon
udon 01039 11229 08040 06161 soy
udon 01039 04032 06087 08017 soy
udon 01039 12005 06049 06268 lemon
udon 01039 10206 06264 06176 lemon
soup 01088 11229 06049 08040 soy
soup 01085 04066 06182 06087 lemon
soup 01088 10206 06161 08017 soy
soup 01085 04094 06055 06215 lemon
plate 01085 11278 06049 08017 soy
plate 01088 10136 06011 08040 lemon
plate 02007 10156 06055 06247 lemon
salad 02019 06016 06182 06247 lemon
pasta 01063 06016 06008 06247 lemon
udon 01039 11278 06011 06215 soy
"""

DINNER = """
plate 01085 11288 06055 08017 soy
plate 01088 11288 06011 06049 lemon
plate 01085 11229 06008 08040 soy
plate 01088 11229 06264 06247 lemon
plate 01085 11278 06161 06176 soy
plate 01088 11278 06087 06182 lemon
plate 01085 10136 06055 06215 lemon
plate 01088 10136 06049 08017 soy
plate 01085 10156 06011 06049 lemon
plate 01088 10156 06008 06182 lemon
plate 01085 10206 08040 06161 soy
plate 01088 10206 06055 06247 lemon
plate 01085 04032 06011 06049 soy
plate 01088 04032 06087 06176 lemon
plate 01085 12005 06055 06247 lemon
plate 01088 12005 06008 08040 soy
plate 01085 04066 06049 06268 lemon
plate 01088 04066 08017 06161 soy
plate 01085 04094 06264 06247 lemon
plate 01088 04094 06011 08040 soy
plate 01085 06016 06055 06182 lemon
plate 01088 06016 06049 06087 soy
plate 01085 04046 06065 06247 lemon
plate 01088 04046 08017 06161 soy
plate 02007 11288 06087 06055 lemon
plate 02007 11229 06011 06182 lemon
plate 02007 10136 06008 06049 lemon
plate 02007 04094 08040 06161 soy
salad 02019 11278 06065 06247 lemon
salad 02019 10156 06011 06182 lemon
salad 02019 10206 06055 06176 lemon
salad 02019 04032 06008 06182 lemon
salad 02019 04094 06065 06247 lemon
salad 01085 12005 06065 06176 lemon
salad 01085 06016 06008 06182 lemon
salad 01088 04066 06065 06247 lemon
pasta 01063 11288 06055 08040 soy
pasta 01063 10136 06182 06087 lemon
pasta 01063 10156 06182 06065 lemon
pasta 01063 11278 06011 06176 lemon
pasta 01063 04032 06049 06268 lemon
pasta 01063 04066 06008 08017 soy
pasta 01063 04094 06182 06247 lemon
pasta 01063 12005 06055 08040 soy
udon 01039 11288 06087 08017 soy
udon 01039 04032 06049 06161 soy
udon 01039 12005 06011 08040 soy
udon 01039 10136 06055 06215 lemon
soup 01088 11278 06161 08040 soy
soup 01085 04032 06049 06087 soy
soup 01088 04094 06182 06055 lemon
soup 01085 10206 06008 08017 lemon
plate 01085 11288 06161 06176 lemon
plate 01088 10206 06011 06049 lemon
plate 02007 12005 06008 06247 lemon
salad 02019 06016 06065 06049 lemon
pasta 01063 06016 06055 08040 soy
udon 01039 04066 06087 06176 lemon
"""

PORTIONS = {
    "01088": 240, "01085": 240, "01039": 260, "01063": 85,
    "02019": 320, "02007": 280,
    "11288": 100, "11229": 110, "11278": 100,
    "10136": 100, "10156": 90, "10206": 120,
    "04032": 220, "12005": 100, "04066": 150,
    "04094": 160, "06016": 140, "04046": 80,
}
STYLE_NAMES = {
    "oats": ("碗", "bowl", "ボウル"),
    "toast": ("早餐", "breakfast", "朝食"),
    "plate": ("餐", "plate", "プレート"),
    "salad": ("沙拉", "salad", "サラダ"),
    "pasta": ("", "", ""),
    "udon": ("", "", ""),
    "soup": ("汤饭", "soup", "スープ"),
}


def instructions(style, parts):
    """State-aware steps with the actual ingredient amounts in each language."""
    from .seed import INGREDIENTS as ORIGINAL

    names = {x[0]: x[1:4] for x in [*ORIGINAL, *INGREDIENTS]}
    lists = [
        "、".join(f"{names[c][i]} {g}g" for c, g in parts.items())
        for i in range(3)
    ]
    actions = {
        "oats": (
            "燕麦用配方中的奶或豆浆加热泡软；若未列奶类则使用饮用水。将列出的熟食材切小块，水果洗净取可食部，与燕麦分别装碗。",
            "Soften oats with the listed milk or soy milk, or drinking water if neither is listed. Cut prepared ingredients and serve alongside the oats.",
            "オーツは記載のミルク・豆乳、なければ飲用水で戻します。調理済み食材を切り、果物の可食部とともに盛ります。",
        ),
        "toast": (
            "面包直接切片装盘；鸡蛋、豆类或鸡肉切碎或压成粗泥铺在面包上。蔬菜、水果和奶类在旁分装。",
            "Slice and plate the bread. Chop or mash the listed cooked egg, beans or chicken for topping; serve vegetables, fruit and dairy alongside.",
            "パンを切って盛り、記載の加熱済み卵・豆・鶏肉を刻むかつぶしてのせます。野菜・果物・乳製品は添えます。",
        ),
        "plate": (
            "主食与已熟主菜温热后分别装盘。水煮蔬菜沥去多余水分；生食蔬果洗净切块，在旁搭配。",
            "Warm the prepared staple and main ingredients and plate separately. Drain boiled vegetables; wash and cut raw produce to serve alongside.",
            "調理済みの主食と主菜を温めて盛ります。ゆで野菜は水を切り、生食の野菜・果物は洗って切り添えます。",
        ),
        "salad": (
            "将已熟主食和主菜放至适口温度后切成小块，水煮蔬菜沥水，生食蔬菜洗净切块。拌匀后立即装盘食用。",
            "Cut prepared staple and protein into pieces at serving temperature. Drain boiled vegetables, wash raw vegetables, toss together and serve promptly.",
            "調理済みの主食・主菜を食べやすく切り、水を切ったゆで野菜と洗った生野菜を合わせ、和えたらすぐに供します。",
        ),
        "pasta": (
            "意面按干重称量，放入小锅，逐次加饮用水煮至软熟，保留少量汤汁不倒掉。拌入列出的已熟主菜及水煮蔬菜；生食番茄、黄瓜、甜椒洗净切块，离火后加入。",
            "Weigh pasta dry. Simmer in a small pot, adding drinking water gradually until tender; retain the small amount of cooking liquid. Fold in prepared protein and boiled vegetables; add washed raw tomato, cucumber or pepper off the heat.",
            "パスタは乾燥重量で量り、小鍋で飲用水を少しずつ足して柔らかく煮ます。残った少量の煮汁は捨てず、調理済み主菜・ゆで野菜を和え、生のトマト・きゅうり・パプリカは洗って切り火を止めて加えます。",
        ),
        "udon": (
            "乌冬面按煮熟后的重量称量，温热后装碗。加入切好的已熟主菜和沥水的水煮蔬菜，拌匀。",
            "Weigh udon in its cooked state, warm and place in a bowl. Add cut prepared protein and drained boiled vegetables and toss.",
            "うどんはゆで上がり重量で量り、温めて器に入れます。切った加熱済み主菜と水を切ったゆで野菜を和えます。",
        ),
        "soup": (
            "熟米饭加饮用水约200～300毫升小火温热，加入切好的已熟主菜和水煮蔬菜，煮至整体热透。生食番茄如有列出，洗净切块后离火加入。",
            "Warm cooked rice gently with about 200–300ml drinking water. Add prepared protein and boiled vegetables and heat through. If listed, wash and chop raw tomato and add off the heat.",
            "調理済みごはんに飲用水約200～300mlを加え、加熱済み主菜・ゆで野菜とともに温めます。生トマトがあれば洗って切り、火を止めて加えます。",
        ),
    }
    action = actions[style]
    seasoning = [
        ("按列示克数加入橄榄油。" if "14001" in parts else "")
        + ("按列示克数加入酱油。" if "17007" in parts else "")
        + ("用列示柠檬汁拌匀。" if "07156" in parts else ""),
        ("Add exactly the listed olive oil. " if "14001" in parts else "")
        + ("Add exactly the listed soy sauce. " if "17007" in parts else "")
        + ("Dress with the listed lemon juice. " if "07156" in parts else ""),
        ("記載量のオリーブ油を加えます。" if "14001" in parts else "")
        + ("記載量のしょうゆを加えます。" if "17007" in parts else "")
        + ("記載量のレモン汁で和えます。" if "07156" in parts else ""),
    ]
    return dict(zip(("zh", "en", "ja"), [
        f"1. 用料（基准份量）：{lists[0]}。\n"
        "2. 按食材名称标注的状态称重：熟饭、肉鱼、蛋和水煮蔬菜按熟重；燕麦、干意面按干重；水果及毛豆按去皮/去壳可食部。肉鱼蛋先充分做熟，豆类及蔬菜按标注状态备好。\n"
        f"3. {action[0]}\n4. {seasoning[0]}不另加盐、汤块或未列出的调味料；纳豆不加附带料包。选择调整份量时，各食材克数以页面配料清单为准。",
        f"1. Base serving ingredients: {lists[1]}.\n"
        "2. Weigh in the named state: rice, meat, fish, eggs and boiled vegetables after cooking; oats and dry pasta before cooking; fruit and edamame as edible flesh. Fully cook meat, fish and eggs first; prepare beans and vegetables in their specified states.\n"
        f"3. {action[1]}\n4. {seasoning[1]}Do not add salt, stock cubes or unlisted condiments; omit natto sauce packets. For scaled servings, use the ingredient amounts shown on the page.",
        f"1. 基準量の材料：{lists[2]}。\n"
        "2. 名称に記載した状態で計量します。ごはん・肉魚・卵・ゆで野菜は調理後、オーツ・乾燥パスタは乾燥重量、果物・枝豆は可食部です。肉魚卵は十分に加熱し、豆類・野菜も表示の状態に調理します。\n"
        f"3. {action[2]}\n4. {seasoning[2]}塩・だしの素・記載のない調味料や納豆のたれは加えません。量を変更した場合は画面の材料一覧のグラム数を使います。",
    ]))


def _recipe(meal, number, style, title_codes, parts):
    rid = f"r178-{meal[0]}{number:03d}"
    suffix = STYLE_NAMES[style]
    titles = {}
    for i, lang in enumerate(("zh", "en", "ja")):
        separator = ("·", ", ", "・")[i]
        words = [LABELS[c][i] for c in title_codes]
        if style == "soup" and lang == "zh":
            words[-1] = words[-1].removesuffix("饭")
        if style == "soup" and lang == "ja":
            words[-1] = words[-1].replace("ごはん", "ライス")
        if style == "udon" and lang == "zh":
            words[-1] = "拌" + words[-1]
        titles[lang] = separator.join(words) + (
            " " if lang == "en" and suffix[i] else ""
        ) + suffix[i]
    return {
        "id": rid, "version": VERSION, "meal": meal, "name": titles,
        "ingredients": parts,
        "data": {
            "image": f"/api/recipe-images/{rid}",
            "image_kind": "original_svg_illustration",
            "art": style,
            "minutes": 20 if meal == "breakfast" else 35,
            "scales": [0.8, 1.0, 1.2, 1.4],
            "instructions": instructions(style, parts),
            "review": "authored_recipe_not_dietitian_reviewed",
            "recipe_source": "application_authored",
            "catalog_version": VERSION,
            "purchase_cost_available": False,
            "nutrition_method": "sum_of_ingredients_in_named_state",
        },
    }


def recipes():
    result = []
    for i, line in enumerate(BREAKFAST.strip().splitlines(), 1):
        style, title, values = line.split("|")
        parts = {c: int(g) for c, g in (p.split(":") for p in values.split())}
        result.append(_recipe("breakfast", i, style, title.split(), parts))
    for meal, text in (("lunch", LUNCH), ("dinner", DINNER)):
        for i, line in enumerate(text.strip().splitlines(), 1):
            style, staple, protein, veg1, veg2, dressing = line.split()
            parts = {staple: PORTIONS[staple], protein: PORTIONS[protein],
                     veg1: 100, veg2: 80, "14001": 8}
            parts.update({"07156": 10} if dressing == "lemon" else {"17007": 4})
            result.append(_recipe(meal, i, style, [protein, veg1, veg2, staple], parts))
    return result
