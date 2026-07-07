"""Human approval gate — terminal review of candidate hypotheses/operators."""
from __future__ import annotations

from . import genome
from .evidence import Store


def review_candidates(auto: str | None = None) -> dict:
    """Interactively (or with auto='accept'/'reject' for scripting) review
    hypotheses that reached a verdict but haven't been human-decided."""
    store = Store()
    pending = [h for h in store.hypotheses()
               if h["status"] in ("supported", "undecided", "falsified")]
    decided = {"accepted": 0, "rejected": 0, "skipped": 0}

    if not pending:
        print("No candidates awaiting review.")
        store.close()
        return decided

    for h in pending:
        print("\n" + "-" * 60)
        print(f"[{h['status']}] {h['text']}")
        if h.get("reason"):
            print(f"  reason: {h['reason']}")
        ev = store.evidence(hypothesis_id=h["id"], promotable_only=True)
        print(f"  promotable evidence rows: {len(ev)}")

        if auto in ("accept", "reject"):
            choice = auto[0]
        else:
            try:
                choice = input("  [a]ccept / [r]eject / [s]kip > ").strip().lower()[:1]
            except (EOFError, KeyboardInterrupt):
                choice = "s"

        if choice == "a":
            store.set_hypothesis_status(h["id"], "accepted", h.get("reason", ""))
            genome.add_record("finding", h["text"][:80],
                              recipe={"claim": h["text"]}, provenance=[e["id"] for e in ev],
                              notes="human-accepted")
            decided["accepted"] += 1
            print("  -> accepted (added to genome)")
        elif choice == "r":
            store.set_hypothesis_status(h["id"], "rejected", h.get("reason", ""))
            decided["rejected"] += 1
            print("  -> rejected")
        else:
            decided["skipped"] += 1
            print("  -> skipped")

    store.close()
    return decided
