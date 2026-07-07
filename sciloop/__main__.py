"""SciLoop CLI — a terminal-native closed scientific runtime.

Subcommands:
  init                        create the workspace
  solve "<question>"          run the discovery loop
  icgg                        run grammar-evolution (ICGG) alone
  transfer                    cross-family transfer matrix
  evidence ls|show <id>       inspect the evidence store
  review                      human approval of candidates
  paper <run_id>              emit a markdown research paper
  status                      workspace / genome / ecology summary
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, ecology, genome
from .evidence import Store


def _term_print(msg=""):
    print(msg, flush=True)


def cmd_init(args):
    ws = config.ensure_workspace()
    Store().close()  # create db
    print(f"workspace: {ws}")
    print(f"LLM: {'configured' if config.llm_available() else 'NOT configured (degraded mode)'}")
    if not config.llm_available():
        print("  set OPENROUTER_API_KEY to enable the debate/experiment authoring stages.")


def cmd_solve(args):
    from . import loop
    res = loop.run(args.question, panel_names=(args.agents.split(",") if args.agents else None),
                   cycles=args.cycles, printer=_term_print,
                   run_icgg_domain=(None if args.no_icgg else args.icgg_domain))
    print("\n== SUMMARY ==")
    print(f"run_id: {res['run_id']}")
    print(f"evidence: {res['evidence_counts']}")
    for c in res["cycles"]:
        print(f"  cycle {c['cycle']}: [{c['verdict']}] {c['hypothesis'][:80]}")
    if res.get("icgg"):
        print(f"  icgg reduction: {res['icgg']['expanded_reduction']} nodes/task; "
              f"operators: {[o['name'] for o in res['icgg']['certified_operators']]}")
    print(f"\nnext: python -m sciloop review   |   python -m sciloop paper {res['run_id']}")
    if args.json:
        print("\n" + json.dumps(res, indent=2, default=str))


def cmd_icgg(args):
    from .icgg import runner
    res = runner.run_growth(args.domain, generations=args.generations, seeds=args.seeds)
    res.pop("grammar", None)
    if args.json:
        print(json.dumps(res, indent=2))
        return
    print(f"\n=== ICGG grammar growth: {args.domain} ===")
    print(f"before mean_expanded: {res['before']['mean_expanded']:.1f}  "
          f"(solve_rate {res['before']['solve_rate']:.2f})")
    print(f"after  mean_expanded: {res['after']['mean_expanded']:.1f}  "
          f"(solve_rate {res['after']['solve_rate']:.2f})")
    print(f"reduction: {res['expanded_reduction']} nodes/task\n")
    print("certified operators (kept only if they beat base + random + freq controls):")
    if not res["certified_operators"]:
        print("  (none certified)")
    for c in res["certified_operators"]:
        print(f"  {c['name']:28s} base={c['base_expanded']:.0f} macro={c['macro_expanded']:.0f} "
              f"rand={c['random_expanded']:.0f} freq={c['freq_expanded']:.0f}  ({c['reason']})")


def cmd_transfer(args):
    from .icgg import runner
    doms = args.domains.split(",") if args.domains else ["arith", "strings", "vector"]
    res = runner.transfer_matrix(doms, seeds=args.seeds)
    if args.json:
        print(json.dumps(res, indent=2)); return
    print("\n=== Cross-family transfer (reduction in nodes/task; diag=within-family) ===")
    print("grown-on \\ tested-on   " + "  ".join(f"{d:>10}" for d in doms))
    for src in doms:
        row = "  ".join(f"{res['matrix'][src][t]['reduction']:>10.1f}" for t in doms)
        print(f"{src:>20}   {row}")


def cmd_evidence(args):
    store = Store()
    if args.action == "show" and args.id:
        e = store.get_evidence(args.id)
        print(json.dumps(e, indent=2, default=str) if e else "not found")
    else:
        run = store.latest_run()
        rows = store.evidence(run_id=run["id"]) if run else []
        print(f"run {run['id'] if run else '(none)'} — {len(rows)} evidence rows")
        for e in rows[:40]:
            print(f"  {e['id']}  [{e['kind']:16s}] {e['source_ref']:14s} {e['content'][:70]!r}")
    store.close()


def cmd_review(args):
    from . import review
    review.review_candidates(auto=args.auto)


def cmd_paper(args):
    from . import paper
    store = Store()
    rid = args.run_id or (store.latest_run() or {}).get("id")
    if not rid:
        print("no run to render"); store.close(); return
    path = paper.generate(store, rid)
    store.close()
    print(f"paper written: {path}")
    print(open(path).read())


def cmd_status(args):
    config.ensure_workspace()
    store = Store()
    runs = store.con.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"]
    hyps = store.con.execute("SELECT COUNT(*) c FROM hypotheses").fetchone()["c"]
    ev = store.con.execute("SELECT COUNT(*) c FROM evidence").fetchone()["c"]
    print(f"workspace : {config.WORKSPACE}")
    print(f"LLM       : {'configured' if config.llm_available() else 'degraded (no key)'}")
    print(f"runs      : {runs}   hypotheses: {hyps}   evidence: {ev}")
    print(f"ecology   : {ecology.summary(store)}")
    print(f"genome    : {genome.summary()}")
    store.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sciloop", description="Closed scientific runtime")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    s = sub.add_parser("solve"); s.add_argument("question")
    s.add_argument("--agents", default=""); s.add_argument("--cycles", type=int, default=2)
    s.add_argument("--icgg-domain", default="arith")
    s.add_argument("--no-icgg", action="store_true")
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_solve)

    s = sub.add_parser("icgg"); s.add_argument("--domain", default="arith")
    s.add_argument("--generations", type=int, default=2); s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_icgg)

    s = sub.add_parser("transfer"); s.add_argument("--domains", default="")
    s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_transfer)

    s = sub.add_parser("evidence"); s.add_argument("action", nargs="?", default="ls",
                                                   choices=["ls", "show"])
    s.add_argument("id", nargs="?"); s.set_defaults(func=cmd_evidence)

    s = sub.add_parser("review"); s.add_argument("--auto", choices=["accept", "reject"])
    s.set_defaults(func=cmd_review)

    s = sub.add_parser("paper"); s.add_argument("run_id", nargs="?"); s.set_defaults(func=cmd_paper)

    sub.add_parser("status").set_defaults(func=cmd_status)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
