"""Exact menu search using compact numbers, energy ranges and protein bitsets.

No top-K truncation: every feasible combination is counted and the original
energy/cost/variety score and recipe-ID tie-break are retained.
"""

from bisect import bisect_left, bisect_right
from decimal import Decimal


def animal_food(code):
    # MEXT food groups 10 (fish/shellfish) and 11 (meat). Dairy/egg are allowed
    # by the application's existing ovo-lacto vegetarian option.
    return code[:2] in ("10", "11")


def protein_food(code):
    return animal_food(code) or code.startswith("12") or code in {
        "04032", "04046", "04066", "04094", "06016",
    }


def select_meals(candidates, target, budget, sodium_limit, budget_min=0, required_foods=()):
    required_bits = {food: 1 << i for i, food in enumerate(sorted(set(required_foods)))}
    required_mask = sum(required_bits.values())
    codes = sorted({
        p["code"]
        for group in candidates.values() for meal in group
        for p in meal["ingredients"] if protein_food(p["code"])
    })
    bits = {c: 1 << i for i, c in enumerate(codes)}

    def compact(m):
        return (
            m["nutrition"]["energy_kcal"], m["cost_jpy"],
            m["sodium_table_upper_mg"],
            sum(bits[p["code"]] for p in m["ingredients"] if p["code"] in bits),
            (m["recipe_id"], m["scale"]), m,
            sum(required_bits[a] for a in set(m.get("allergens", [])) if a in required_bits),
        )

    groups = [
        [compact(m) for m in candidates[k] if m["nutrition"]["energy_kcal"] is not None]
        for k in ("breakfast", "lunch", "dinner")
    ]
    breakfasts, lunches, dinners = groups
    dinners.sort(key=lambda x: (x[0], x[4]))
    energies = [d[0] for d in dinners]
    lunch_repeats = [[(l[3] & d[3]).bit_count() for d in dinners] for l in lunches]
    low, high = target * 0.9, target * 1.1
    best = best_key = None
    feasible = 0
    for b in breakfasts:
        breakfast_repeats = [(b[3] & d[3]).bit_count() for d in dinners]
        for li, l in enumerate(lunches):
            energy_pair, cost_pair, sodium_pair = b[0] + l[0], b[1] + l[1], b[2] + l[2]
            if cost_pair > budget or sodium_pair > sodium_limit:
                continue
            # Expand by a tiny margin, then recheck the original expression
            # inside the loop to preserve floating-point boundary semantics.
            first = bisect_left(energies, low - energy_pair - 1e-9)
            last = bisect_right(energies, high - energy_pair + 1e-9)
            repeats = (b[3] & l[3]).bit_count()
            ld = lunch_repeats[li]
            for di in range(first, last):
                d = dinners[di]
                energy = energy_pair + d[0]
                if not low <= energy <= high:
                    continue
                cost = cost_pair + d[1]
                # At a monetary boundary, compare the same decimal sum used by
                # independent plan validation, not a floating-point artifact.
                if abs(cost - budget_min) < 1e-8 or abs(cost - budget) < 1e-8:
                    cost = float(sum(Decimal(str(m[1])) for m in (b, l, d)))
                if not budget_min <= cost <= budget or sodium_pair + d[2] > sodium_limit:
                    continue
                if (b[6] | l[6] | d[6]) & required_mask != required_mask:
                    continue
                feasible += 1
                repetition = repeats + breakfast_repeats[di] + ld[di]
                score = abs(energy - target) / target * 10 + cost / budget * 0.35 + repetition * 0.08
                if best_key is not None and score > best_key[0]:
                    continue
                key = (score, (b[4], l[4], d[4]))
                if best_key is None or key < best_key:
                    best = [b[5], l[5], d[5]]
                    best_key = key
    return best, feasible
