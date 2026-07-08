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


def cmd_noether(args):
    from . import noether
    doms = args.domains.split(",") if args.domains else ["arith", "strings", "vector"]

    print("=== Computational Noether Engine ===")
    print("Discovering conserved quantities of successful search, deriving symmetry operators,\n"
          "and testing whether they transfer better than syntactic-motif operators.\n")
    per_domain = {}
    for d in doms:
        r = noether.run_cne(d, seeds=args.seeds)
        r.pop("_Q", None)
        per_domain[d] = r
        q = r["conserved_quantity"]
        print(f"[{d}] conserved Q = {q['expression']}")
        print(f"      pos_drift={q['pos_drift']} neg_drift={q['neg_drift']} "
              f"conservation_score={q['conservation_score']}")
        syms = [s for s in r["symmetry_operators"] if s["is_symmetry"]]
        print(f"      symmetry generators: {['+'.join(s['sequence']) for s in syms][:5]}")
        print(f"      certified (beats controls): "
              f"{['+'.join(c['sequence']) for c in r['certified_symmetry_operators']] or '(none)'}")

    print("\n-- HEADLINE: transfer of syntactic vs symmetry operators (nodes/task saved) --")
    cmp = noether.compare_transfer(doms, seeds=args.seeds)
    for label in ("syntactic", "symmetry"):
        print(f"  {label}:")
        for src in doms:
            print("    " + f"{src:>8}: " +
                  "  ".join(f"{t}={cmp[label][src][t]:>6.1f}" for t in doms))

    print("\n-- DIFFICULTY: Q-breaking depth vs log(effort), Spearman --")
    diff = {}
    for d in doms:
        bp = noether.breaking_point_analysis(d, seeds=args.seeds)
        diff[d] = bp["spearman_breakdepth_vs_logeffort"]
        print(f"    {d:>8}: rho = {bp['spearman_breakdepth_vs_logeffort']:+.3f}  (n={bp['n']})")

    if args.json:
        print("\n" + json.dumps({"per_domain": per_domain, "transfer": cmp, "difficulty": diff},
                                indent=2, default=str))


def cmd_adjoint(args):
    from . import adjoint, genome
    doms = args.domains.split(",") if args.domains else ["arith", "strings", "vector"]

    print("=== The Adjoint Engine — learning on the goal side ===")
    print("Co-operators (goal decompositions) learned on ONE domain, applied UNCHANGED to all.\n")

    r = adjoint.adjoint_experiment(doms, seeds=args.seeds)
    print("base BFS mean expanded (test): " +
          "  ".join(f"{d}={r['base_test'][d]['mean_expanded']:.1f}" for d in doms))
    print("\nlearned goal-side policy per source domain:")
    for d in doms:
        print(f"  {d}: {r['learned_policies'][d]}")

    print("\nGOAL-SIDE transfer (reduction in nodes/task; rows=learned-on, cols=applied-to):")
    for src in doms:
        row = "  ".join(f"{t}={r['goal_side'][src][t]['reduction']:>7.1f}"
                        f"(sr={r['goal_side'][src][t]['solve_rate']})" for t in doms)
        print(f"  {src:>8}: {row}")
    print(f"\nrandom-policy control (mean reduction): {r['random_control']}")
    print("\ncompare: forward ICGG macros transfer 0.0 off-diagonal (python -m sciloop transfer)")

    # Integration with the runtime: promote learned co-operators into the
    # evidence store, ecology ledger, and knowledge genome.
    store = Store()
    rid = store.create_run("adjoint-experiment: goal-side transfer", {"domains": doms})
    eid = store.add_evidence(rid, "executed_result", json.dumps(r, default=str)[:18000],
                             source_ref="adjoint")
    for src in doms:
        pol = r["learned_policies"][src]
        if not pol:
            continue
        name = adjoint.policy_name(pol)
        store.add_operator(name, "goal-side", [pol["schema"], str(pol["phi"]), str(pol["R"])],
                           evidence_id=eid)
        offdiag = [r["goal_side"][src][t]["reduction"] for t in doms if t != src]
        win = all(v > 0 for v in offdiag) if offdiag else False
        store.record_operator_use(name, win=win, cost=1.0)
        if not genome.has(name):
            genome.add_record("co_operator", name,
                              recipe={"policy": pol, "learned_on": src},
                              provenance=[eid],
                              notes="goal-side decomposition policy; transfers cross-domain")
    store.finish_run(rid, status="done")
    store.close()
    print(f"\npromoted co-operators recorded in ecology + genome (run {rid}).")

    if args.json:
        print("\n" + json.dumps(r, indent=2, default=str))


def cmd_concepts(args):
    from . import concepts, genome
    print("=== Concept invention (a concept must earn its name) ===\n")
    rep = concepts.invent(seeds=args.seeds)
    print(f"baseline observable: {rep['baseline']['observable']} "
          f"|rho|={rep['baseline']['abs_rho']}  (the bar to beat +0.10)\n")
    print(f"ADMITTED ({len(rep['admitted'])}):")
    for a in rep["admitted"]:
        print(f"  {a['concept']}\n     why: {a['why']}")
    for r in rep["rejected"]:
        print(f"REJECTED: {r['note']}")
    print(f"\nCONCEPT TOWER (level-2, must beat best parent) ({len(rep['tower'])}):")
    for t in rep["tower"]:
        print(f"  {t['concept']}  |rho|={t['abs_rho']} vs parent {t['parent_best']} "
              f"(built from {t['built_from']})")
    g1 = bool(rep["tower"])
    print(f"\nG1 concept-tower gate: {'PASS' if g1 else 'FAIL (no level-2 concept survived)'}")

    store = Store()
    rid = store.create_run("concept-invention", {})
    eid = store.add_evidence(rid, "executed_result", json.dumps(rep)[:18000],
                             source_ref="concepts")
    for a in rep["admitted"][:6]:
        nm = a["concept"].split(":")[0]
        if not genome.has(nm):
            genome.add_record("concept", nm, recipe={"definition": a["concept"]},
                              provenance=[eid], notes=a["why"])
    for t in rep["tower"][:3]:
        nm = t["concept"].replace(" ", "")
        if not genome.has(nm):
            genome.add_record("concept", nm,
                              recipe={"definition": t["concept"], "level": 2,
                                      "built_from": t["built_from"]},
                              provenance=[eid], notes=f"level-2; |rho|={t['abs_rho']}")
    store.finish_run(rid, status="done")
    store.close()
    if args.json:
        print("\n" + json.dumps(rep, indent=2, default=str))


def cmd_evolve(args):
    from . import evolution, genome, reflect
    print("=== Structural evolution of Frames (minds), train-split selection ===\n")
    res = evolution.evolve(pop_size=args.pop, generations=args.generations,
                           seeds=args.seeds, rng_seed=args.rng_seed,
                           printer=lambda m: print(m, flush=True))
    ev, hb = res["evolved_test_fitness"], res["hand_built_test_fitness"]
    print(f"\nHELD-OUT verdict (G2):")
    print(f"  evolved best : {ev['overall']}  per-domain {ev['per_domain']}")
    print(f"  hand-built   : {hb['overall']}  per-domain {hb['per_domain']}")
    print(f"  evolution beats design: {res['evolution_beats_design']}")
    print(f"  evolved frame: {res['best_desc']}")

    print("\n=== Self-reflection: mining rules about how minds improve ===")
    metas = reflect.mine_meta_operators(res["meta_traces"])
    for m in metas:
        print(f"  {m}")

    print("\n=== G3: does meta-knowledge accelerate future evolution? ===")
    g3 = reflect.g3_test(metas, seeds=args.seeds, generations=3, pop=6)
    for p in g3.get("pairs", []):
        print(f"  seed {p['rng_seed']}: biased={p['biased_final_best']} "
              f"uniform={p['uniform_final_best']}")
    print(f"  verdict: {g3['verdict']}")

    store = Store()
    rid = store.create_run("structural-evolution", {})
    eid = store.add_evidence(rid, "executed_result",
                             json.dumps({k: v for k, v in res.items() if k != 'meta_traces'},
                                        default=str)[:18000],
                             source_ref="evolution")
    eid3 = store.add_evidence(rid, "executed_result", json.dumps(g3, default=str)[:8000],
                              source_ref="reflect:g3")
    if not genome.has("best_evolved_frame"):
        genome.add_record("frame", "best_evolved_frame",
                          recipe={"frame": res["best_frame"], "desc": res["best_desc"]},
                          provenance=[eid],
                          notes=f"G2 beats design: {res['evolution_beats_design']}")
    for i, m in enumerate([m for m in metas if "motif" in m][:3]):
        nm = "meta_" + "_".join(m["motif"])
        if not genome.has(nm):
            genome.add_record("meta_operator", nm, recipe=m, provenance=[eid3],
                              notes=f"g3: {g3['verdict']}")
    store.finish_run(rid, status="done")
    store.close()
    if args.json:
        print("\n" + json.dumps({"result": {k: v for k, v in res.items() if k != 'meta_traces'},
                                 "g3": g3}, indent=2, default=str))


def cmd_introspect(args):
    from . import reflect
    r = reflect.introspect()
    print(r["report"])


def cmd_ricci(args):
    from . import ricci
    doms = args.domains.split(",") if args.domains else ["arith", "strings", "vector"]

    print("=== Ricci Computing ===")
    print("Curvature of the reachability graph: difficulty at negative-curvature bottlenecks;\n"
          "operators selected by a zero-supervision geometric bridge rule.\n")

    print("-- DIFFICULTY: integrated negative curvature along solution path vs log(effort) --")
    diff = {}
    for d in doms:
        r = ricci.difficulty_analysis(d, seeds=args.seeds)
        diff[d] = r
        c = r["curvature"]
        print(f"  [{d}] graph edges={c.get('edges')} frac_negative={c.get('frac_negative')} "
              f"mean_curv={c.get('mean')}")
        print(f"        Spearman(neg-curv, log effort) = "
              f"{r['spearman_negcurv_vs_logeffort']:+.3f}  (n={r['n']})")

    print("\n-- A/B: operator selection — frequency (supervised) vs curvature (zero-shot) --")
    ab = ricci.ab_compare(doms, seeds=args.seeds)
    for d in doms:
        arm = ab["arms"][d]
        fa, cb = arm["frequency_supervised"], arm["curvature_zero_shot"]
        print(f"  [{d}]")
        print(f"    supervised : kept={fa['kept'] or '(none)'} best_improvement={fa['best_improvement']}")
        print(f"    zero-shot  : candidates={cb['candidates']}")
        print(f"                 kept={cb['kept'] or '(none)'} best_improvement={cb['best_improvement']}")
        print(f"    zero-shot matches supervised: {arm['zero_shot_matches_supervised']}")

    if args.json:
        print("\n" + json.dumps({"difficulty": diff, "ab": ab}, indent=2, default=str))


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

    s = sub.add_parser("noether"); s.add_argument("--domains", default="")
    s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_noether)

    s = sub.add_parser("ricci"); s.add_argument("--domains", default="")
    s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_ricci)

    s = sub.add_parser("adjoint"); s.add_argument("--domains", default="")
    s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_adjoint)

    s = sub.add_parser("concepts"); s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_concepts)

    s = sub.add_parser("evolve"); s.add_argument("--generations", type=int, default=6)
    s.add_argument("--pop", type=int, default=8); s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--rng-seed", type=int, default=1)
    s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_evolve)

    sub.add_parser("introspect").set_defaults(func=cmd_introspect)

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
