# SciLoop — a terminal-native closed scientific runtime

SciLoop is a research operating system that runs entirely in the terminal. Its
loop does not stop at an answer — it keeps going:

```
Hypothesis → Execute → Measure → Falsify → Compress → Promote → (repeat)
```

Nothing enters the runtime's "grammar" of operators until it has **survived
that loop** — i.e. beaten controls on held-out evidence. The goal is to discover
new computational primitives from execution evidence and let the reasoning
language itself evolve.

## Why it's different
Most agents stop at `LLM → answer` or `LLM → tool → answer`. SciLoop continues:
answer → execution trace → invariant mining → grammar evolution → new operators
→ new runtime → repeat. The **runtime changes**, not just memory.

## Design guarantees
- **Zero third-party dependencies.** Pure Python standard library (LLM calls go
  over `urllib`). Runs on Termux with just `python`. Verify:
  `python -S -c "import sciloop.loop"`.
- **No hallucinations promoted.** Evidence is tiered: only `executed_result`
  (code that actually ran in the sandbox) and `retrieved_source` justify a
  verdict. `agent_claim` (what an agent *said*) is recorded but never sufficient.
- **Degrades honestly.** Without a key, the debate/experiment-authoring stages
  are skipped, but the sandbox, execution geometry, invariant battery, grammar
  evolution, evidence store, review, and paper generator all still run.

## Install / run
```bash
# Termux or any machine with Python 3.10+
pkg install python           # (Termux)  — nothing else needed
export OPENROUTER_API_KEY=sk-or-...   # optional; enables the debate + experiments
export SCILOOP_MODEL=meta-llama/llama-3.3-70b-instruct:free   # optional override

python -m sciloop init
python -m sciloop solve "Does feedback drive specialization in complex systems?" \
                        --agents math,physics,cs,critic,devil --cycles 2
python -m sciloop icgg --domain arith --seeds 3         # grammar evolution alone
python -m sciloop transfer                              # cross-family transfer matrix
python -m sciloop review                                # human approval gate
python -m sciloop paper <run_id>                        # emit a markdown paper
python -m sciloop status                                # workspace / ecology / genome
```

## The pipeline (modules)
| Stage | Module | What it does |
|---|---|---|
| Problem Compiler | `compiler.py` | question → falsifiable hypotheses + experiments |
| Debate Network | `agents.py` | 9 specialist agents (incl. Devil's Advocate) debate |
| Evidence Store | `evidence.py` | SQLite, provenance-tiered (no-hallucination rule) |
| Execution Engine | `sandbox.py` | isolated `python -I -E -B`, secrets scrubbed, rlimits |
| Execution Geometry | `geometry.py` | `sys.settrace`+`ast` → AST/call-graph/trace features |
| Invariant Discovery | `invariants.py` | observable battery, Spearman, coarse-grain stability R |
| Grammar Evolution | `icgg/` | mine motifs → **certify vs controls on held-out** → promote |
| Operator Ecology | `ecology.py` | fitness ledger; weak operators retire |
| Knowledge Genome | `genome.py` | "reasoning DNA" (JSONL) with provenance |
| Paper Generator | `paper.py` | markdown paper citing evidence ids |
| Human Approval | `review.py` | `[a]ccept / [r]eject / [s]kip` |
| The Spine | `loop.py` | Hypothesis→Execute→Measure→Falsify→Compress→Promote |

## What actually works today (measured, not claimed)
- Certified grammar growth **halves search effort** on held-out tasks and only
  keeps macros that beat base, random-macro, and frequency-macro controls
  (arith 84→42, strings 111→49, vector 217→83 nodes/task).
- The cross-family transfer matrix currently shows macros are **family-specific**
  (they help within a family, not across) — a real, falsifiable negative result.

## The Computational Noether Engine (`noether.py`) — a novel method

Noether's theorem run **backwards on a search process**: every symmetry of a
system's dynamics has a conserved quantity. CNE (a) discovers a quantity `Q`
over execution-geometry observables that stays constant along *successful*
trajectories but not random ones (a "conservation law of good reasoning"),
(b) finds the operator compositions that leave `Q` invariant (its symmetry
generators), and (c) tests whether those symmetry operators **transfer** across
domains better than syntactic-motif operators.

Run it: `python -m sciloop noether --domains arith,strings,vector`

**Measured verdict (honest, and the whole point):**
- **Conservation — confirmed.** On arith, CNE discovers `Q = reach − openness`
  with a conservation score ~130–170 (nearly constant on solved traces, wild on
  random walks). Its symmetry generators are automatically the **group inverses**
  (`add1+sub1`, `double+halve`) — an interpretable, correct rediscovery.
- **Transfer hypothesis — FALSIFIED here.** Those symmetries are inverse
  *identities*, so they don't speed search and don't transfer (≈0 everywhere),
  while syntactic macros still help only within-family. The headline claim did
  not survive contact with evidence — recorded, not hidden.
- **Difficulty prediction — confirmed.** The step where `Q` first *breaks* its
  band predicts effort: Spearman(Q-break depth, log effort) ≈ **−0.66 (arith)**
  and **+0.44 … +0.99 (vector)** across seed counts — comparable to the strongest
  known trace-difficulty signal (first-conflict depth). One mechanism yielded a
  real difficulty observable even though its operator-transfer claim failed.

This is the intended behaviour: a genuinely novel, falsifiable method, built and
then *measured* — delivering one confirmed prediction, one interpretable
discovery, and one clean negative result.

## Ricci Computing (`ricci.py`) — curvature of the reasoning graph

Idea: the reachability graph of a search process has intrinsic (Forman-Ricci)
curvature; difficulty lives at negative-curvature bottlenecks; and operators
should be *selected by geometry* (bridge the bottlenecks) rather than by
frequency — because a geometric rule is coordinate-free and can run unchanged
in every domain with **zero success-trace supervision**.

Run it: `python -m sciloop ricci --domains arith,strings,vector`

**Measured verdict (3 seeds, 75 tasks/domain):**
- **Difficulty — strongest signal yet, but not universal.** Integrated negative
  curvature along the solution path vs log(effort): **arith ρ = +0.839** (beats
  first-conflict depth's +0.763 and CNE's −0.66), strings +0.31 (weak),
  vector −0.17 (null). Confirmed in one domain, not all — reported as such.
- **Zero-shot operator placement — FALSIFIED (v1 rule).** The pure
  bridge-the-most-negative-curvature rule selected *regressive* sequences
  (`down+down+left`, `triple+halve`); none survived certification, while
  supervised frequency mining kept strong macros in all three domains
  (improvements 32–96). Geometry alone knows where the bottlenecks are but not
  *which way through them* — the rule needs a directionality term.
- **Structural diagnosis (why):** the sampled reachability graphs are
  triangle-free (frac_negative ≈ 1.0 everywhere), so Forman curvature collapses
  to degree structure — search graphs are near-trees (hyperbolic). Testing the
  full idea properly needs Ollivier curvature (transport-based) and/or richer
  domains whose graphs contain cycles/triangles. That is the concrete,
  falsifiable next step this experiment earned.

## What is a hypothesis, not a guarantee
Whether execution geometry contains *transferable* invariants, and whether
evolving the grammar beats existing abstraction-learning methods, are open
empirical questions. SciLoop is the machine for testing them one certified step
at a time — the gates (P4–P7) only open on measured wins.

*Phases 4–7 (full operator ecology dynamics, genome regeneration, richer paper
generation, self-tuning runtime) are scaffolded and gated on results from the
current phases.*
