import json
import math
import os
from typing import Dict, List, Tuple


def apply_lod_selection(total: int, lod_scores: List[float], selected_idx: int, z: float, lod_enabled: bool) -> Tuple[int, bool, bool]:
    """
    Simulate the selection rules from project.html applyLOD for visibility count.
    Returns: (visible_count, contains_selected, selected_only)
    """
    base_total = total
    if base_total != len(lod_scores):
        raise ValueError("total must match lod_scores length")

    # If LOD disabled or small graph or near/full zoom => show all
    if (not lod_enabled) or base_total <= 150 or z >= 0.8:
        visible = set(range(base_total))
        return len(visible), (selected_idx in visible if selected_idx is not None else False), (len(visible) == 1)

    # Compute thresholds
    min_visible = min(80, math.ceil(base_total * 0.2))
    target_ratio = 0.25 if z < 0.4 else 0.6
    desired_visible = max(min_visible, math.ceil(base_total * target_ratio))

    # Rank by score desc
    ranked = sorted(range(base_total), key=lambda i: lod_scores[i], reverse=True)

    # Mid zoom: keep all displayed (opacity fade). Visible = all
    if 0.4 <= z < 0.8:
        visible = set(range(base_total))
        if selected_idx is not None:
            visible.add(selected_idx)
        return len(visible), (selected_idx in visible if selected_idx is not None else False), (len(visible) == 1)

    # Low zoom: show top desired
    visible = set(ranked[:desired_visible])
    if selected_idx is not None:
        visible.add(selected_idx)

    # Safety: ensure at least min_visible
    if len(visible) < min_visible:
        visible = set(ranked[:min_visible])
        if selected_idx is not None:
            visible.add(selected_idx)

    return len(visible), (selected_idx in visible if selected_idx is not None else False), (len(visible) == 1)


def run_checks() -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}

    # Case A: large graph, low zoom => should keep >= minVisible and not only selected
    total = 300
    lod_scores = [i / total for i in range(total)]  # increasing scores
    selected_idx = 0
    z = 0.3
    vc, has_sel, only_sel = apply_lod_selection(total, lod_scores, selected_idx, z, True)
    min_visible = min(80, math.ceil(total * 0.2))
    out["case_A"] = {
        "visible_count": vc,
        "has_selected": has_sel,
        "selected_only": only_sel,
        "min_visible": min_visible,
        "pass": (vc >= min_visible and not only_sel),
    }

    # Case B: small/medium graph => all visible even at low zoom
    total = 120
    lod_scores = [0.5] * total
    vc, has_sel, only_sel = apply_lod_selection(total, lod_scores, 5, 0.3, True)
    out["case_B"] = {
        "visible_count": vc,
        "expected": total,
        "pass": (vc == total),
    }

    # Case C: near/full zoom => all visible
    total = 500
    lod_scores = [0.1] * total
    vc, has_sel, only_sel = apply_lod_selection(total, lod_scores, 10, 0.9, True)
    out["case_C"] = {
        "visible_count": vc,
        "expected": total,
        "pass": (vc == total),
    }

    # Case D: mid zoom => all displayed (opacity fade), count == total
    total = 500
    lod_scores = [0.1] * total
    vc, has_sel, only_sel = apply_lod_selection(total, lod_scores, 10, 0.5, True)
    out["case_D"] = {
        "visible_count": vc,
        "expected": total,
        "pass": (vc == total),
    }

    # Case E: LOD disabled => all visible regardless of zoom/size
    total = 500
    lod_scores = [0.1] * total
    vc, has_sel, only_sel = apply_lod_selection(total, lod_scores, None, 0.2, False)
    out["case_E"] = {
        "visible_count": vc,
        "expected": total,
        "pass": (vc == total),
    }

    # Aggregate
    out["summary"] = {
        "all_pass": all(v.get("pass", False) for k, v in out.items() if k.startswith("case_")),
        "cases_total": len([k for k in out.keys() if k.startswith("case_")]),
    }
    return out


def main() -> None:
    results = run_checks()
    os.makedirs(os.path.dirname("scripts/tests/json-result.json"), exist_ok=True)
    with open("scripts/tests/json-result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()


