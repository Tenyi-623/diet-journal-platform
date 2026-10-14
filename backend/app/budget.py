"""Budget range extraction and propagation; a ceiling alone has no lower bound."""

import re
import unicodedata
from .feedback import ResultCheckError

_CJK = "零〇一二三四五六七八九两兩十百千万壹贰貳叁參肆伍陆陸柒捌玖拾佰仟萬"
_NUMBER = rf"(?<![\d.{_CJK}])(\d+(?:,\d{{3}})*(?:\.\d+)?|[{_CJK}]+)(?![\d.{_CJK}])"
_UNIT = r"(?:日元|円|yen|JPY)"
_JOIN = r"(?:-|–|—|~|〜|至|到|から|and|to)"
_RANGE = rf"(?:¥\s*|JPY\s*)?{_NUMBER}\s*(?:{_UNIT})?\s*{_JOIN}\s*(?:¥\s*|JPY\s*)?{_NUMBER}\s*(?:{_UNIT})?"
_AMOUNT = rf"(?:¥\s*|JPY\s*)?{_NUMBER}\s*(?:{_UNIT})?"
_MEAL = r"早餐|午餐|晚餐|早饭|午饭|晚饭|早上|朝食|昼食|夕食|breakfast|lunch|dinner|每餐|一餐|per meal"
_EN_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


def _normalized(message):
    message = unicodedata.normalize("NFKC", message)
    words = "|".join([*_EN_NUMBERS, "hundred", "thousand"])
    def replace(match):
        total = section = 0
        for word in re.split(r"[\s-]+", match.group().lower()):
            if word == "hundred":
                section = (section or 1) * 100
            elif word == "thousand":
                total += (section or 1) * 1000
                section = 0
            else:
                section += _EN_NUMBERS[word]
        return str(total + section)
    # Do not consume "and": it separates the two ends of a "between ... and ..." range.
    return re.sub(rf"\b(?:{words})(?:[\s-]+(?:{words}))*\b", replace, message, flags=re.IGNORECASE)


def _integer(token):
    token = token.replace(",", "")
    if token.isascii():
        if not token.isdigit():
            raise ResultCheckError("invalid_budget_range")
        return int(token)
    token = token.translate(str.maketrans("〇两兩壹贰貳叁參肆伍陆陸柒捌玖拾佰仟萬", "零二二一二二三三四五六六七八九十百千万"))
    digits = {c: n for n, c in enumerate("零一二三四五六七八九")}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    if not any(c in units for c in token):
        return int("".join(str(digits[c]) for c in token))
    # Colloquial "一千五" can mean 1500 or 1005: require the full amount.
    if len(token) >= 2 and token[-1] in digits and token[-2] in "百千万":
        raise ResultCheckError("invalid_budget_range")
    total = section = number = 0
    previous_unit = 10000
    for c in token:
        if c in digits:
            number = digits[c]
        elif c == "万":
            total += (section + number) * 10000
            section = number = 0
            previous_unit = 10000
        else:
            unit = units[c]
            if unit >= previous_unit:
                raise ResultCheckError("invalid_budget_range")
            section += (number or 1) * unit
            number = 0
            previous_unit = unit
    return total + section + number


def _money_context(normalized, match):
    prefix = normalized[max(0, match.start() - 20):match.start()]
    suffix = normalized[match.end():match.end() + 12]
    clause_prefix = re.split(r"[，,。;；\n]", normalized[:match.start()])[-1]
    if re.search(_MEAL, clause_prefix, re.IGNORECASE):
        # "早餐...，一日预算..." is split at punctuation; a per-meal amount
        # must not become a total-day constraint.
        if not re.search(r"一日|一天|全天|每天|每日|合计|合計|daily|per day", clause_prefix, re.IGNORECASE):
            return False
    money = re.search(_UNIT + r"|¥", match.group(), re.IGNORECASE)
    budget_prefix = re.search(r"(?:预算|預算|予算|budget)\s*(?:为|是|在|は|:|of|is|between)?\s*$", prefix, re.IGNORECASE)
    other_unit = re.match(r"\s*(?:kcal|卡|千卡|克|mg|g\b|分钟|分|岁|歳)", suffix, re.IGNORECASE)
    return bool(money or (budget_prefix and not other_unit))


def valid_interval(lower, upper):
    return lower is None or (
        upper is not None and 100 <= lower <= upper <= 20000
    )


def explicit_budget_range(message):
    normalized = _normalized(message)
    found = []
    for match in re.finditer(_RANGE, normalized, re.IGNORECASE):
        if not _money_context(normalized, match):
            continue
        lower, upper = (_integer(v) for v in match.groups())
        if not valid_interval(lower, upper):
            raise ResultCheckError("invalid_budget_range")
        found.append((lower, upper))
    if len(set(found)) > 1:
        # Conflicting/multiple ranges need clarification, not an arbitrary choice.
        raise ResultCheckError("ambiguous_budget_range")
    return found[0] if found else None


def current_budget(message):
    """Return (ceiling, floor) from this message, independently of model/history."""
    interval = explicit_budget_range(message)
    normalized = _normalized(message)
    range_spans = [m.span() for m in re.finditer(_RANGE, normalized, re.IGNORECASE)]
    ceilings = set()
    for match in re.finditer(_AMOUNT, normalized, re.IGNORECASE):
        if any(start <= match.start() < end for start, end in range_spans):
            continue
        if not _money_context(normalized, match):
            continue
        prefix = normalized[max(0, match.start() - 20):match.start()]
        if re.search(r"至少|最低|下限|以上|at least|minimum", prefix, re.IGNORECASE):
            raise ResultCheckError("invalid_budget_range")
        amount = _integer(match.group(1))
        if not 100 <= amount <= 20000:
            raise ResultCheckError("invalid_budget_range")
        ceilings.add(amount)
    if interval:
        lower, upper = interval
        if ceilings - {upper}:
            raise ResultCheckError("ambiguous_budget_range")
        return upper, lower
    if len(ceilings) > 1:
        raise ResultCheckError("ambiguous_budget_range")
    return (next(iter(ceilings)), None) if ceilings else (None, None)


def resolve_budget(upper, lower, previous_plan=None):
    """An explicit new ceiling clears a previous floor; otherwise retain a range."""
    if upper is None and lower is None and previous_plan and previous_plan.get("budget_jpy") is not None:
        upper = previous_plan["budget_jpy"]
        lower = previous_plan.get("budget_min_jpy")
    if not valid_interval(lower, upper):
        raise ResultCheckError("invalid_budget_range")
    return upper, lower
