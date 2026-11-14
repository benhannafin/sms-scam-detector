"""Score the app on the reference set (Stage 11, decision 040).

Run with:
    python -m training.evaluate_reference              # design half (steps 1 and 2)
    python -m training.evaluate_reference --held-out   # held-out half (step 3 only)
"""
import argparse
from collections import Counter
import csv
import hashlib
from pathlib import Path

REFERENCE_PATH = Path(__file__).resolve().parent.parent / "data" / "reference_set.csv"
LABELS = {"ham", "spam", "smishing"}
ORIGINS = {"verbatim", "modelled", "made_up"}


def load_reference_set(path=REFERENCE_PATH):
    """Return the reference messages as a list of dicts."""
    with open(path, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def split_halves(rows):
    """Return {id: "design" or "held_out"}, split evenly within each class and origin.

    The order comes from a hash of each id, so the split is repeatable without storing it.
    """
    groups = {}
    for row in rows:
        groups.setdefault((row["expected"], row["origin"]), []).append(row["id"])
    halves = {}
    for ids in groups.values():
        ordered = sorted(ids, key=lambda id_: hashlib.sha256(id_.encode()).hexdigest())
        for position, id_ in enumerate(ordered):
            halves[id_] = "design" if position % 2 == 0 else "held_out"
    return halves


def outcome(expected, label):
    """How a result counts. For spam or scam, a "missed" is a confident Looks legitimate."""
    if expected == "ham":
        return {"ham": "correct", "unsure": "unsure"}.get(label, "false alarm")
    return {"ham": "missed", "unsure": "unsure"}.get(label, "caught")


def evaluate(rows, service):
    """Run each message through the check service and record what it said."""
    results = []
    for row in rows:
        result = service.check(row["text"])
        results.append({
            "id": row["id"],
            "expected": row["expected"],
            "origin": row["origin"],
            "label": result.label,
            "status": result.status,
            "confidence": result.confidence,
            "reasons": [reason.text for reason in result.reasons],
            "outcome": outcome(row["expected"], result.label),
        })
    return results


def summarise(results):
    """Count outcomes for each (expected, origin) group."""
    return Counter((r["expected"], r["origin"], r["outcome"]) for r in results)


def print_report(results, half):
    print(f"Reference set, {half} half: {len(results)} messages\n")
    for r in results:
        confidence = "-" if r["confidence"] is None else f"{r['confidence']:.2f}"
        print(f"{r['id']:4} {r['expected']:9} {r['origin']:9} -> {r['label']:8} {confidence:>5}  "
              f"{r['outcome']:12} {'; '.join(r['reasons'])}")
    print("\nSummary (expected, origin: outcome counts)")
    counts = summarise(results)
    for expected, origin in sorted({(r["expected"], r["origin"]) for r in results}):
        outcomes = {o: n for (e, g, o), n in counts.items() if (e, g) == (expected, origin)}
        total = sum(outcomes.values())
        print(f"  {expected:9} {origin:9} ({total}): {outcomes}")


def main(argv=None, service=None):
    parser = argparse.ArgumentParser(description="Score the app on the reference set.")
    parser.add_argument("--held-out", action="store_true", help="score the held-out half (step 3 only)")
    args = parser.parse_args(argv)

    rows = load_reference_set()
    half = "held_out" if args.held_out else "design"
    halves = split_halves(rows)
    chosen = [row for row in rows if halves[row["id"]] == half]

    if service is None:
        from app.check_service import CheckService
        from app.classifier import load_model
        service = CheckService(load_model("v1"))

    results = evaluate(chosen, service)
    print_report(results, half)
    return results


if __name__ == "__main__":
    main()
