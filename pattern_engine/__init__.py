"""pattern_engine — detect recurring structures and analogies across research domains.

Modules:
  pattern_detector   — find recurring structures across hypothesis text
  analogy_engine     — structural similarity mapping between domains (wraps intelligence/)
  causal_candidates  — identify candidate causal relationships from evidence
  graph_patterns     — motif detection in the KG
  temporal_patterns  — track how patterns evolve over time
  compression        — identify minimal description of repeated structure
  novelty            — measure how novel a pattern is vs prior art
  ranking            — rank candidate patterns by evidence strength
"""
from pattern_engine.pattern_detector import detect_patterns
from pattern_engine.analogy_engine import find_cross_domain_analogies
from pattern_engine.novelty import score_novelty
from pattern_engine.ranking import rank_patterns

__all__ = ["detect_patterns", "find_cross_domain_analogies", "score_novelty", "rank_patterns"]
