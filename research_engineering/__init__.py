"""research_engineering — turn validated research ideas into software artifacts.

This module is activated ONLY after a hypothesis has been accepted by a
human reviewer. It must never operate on candidate hypotheses.

Sub-packages:
  algorithm_designer/  — generate algorithm pseudocode and complexity analysis
  architecture/        — system and data-flow design for implementations
  code_generation/     — produce runnable code from accepted hypotheses
  refactoring/         — improve existing implementation quality
  optimization/        — identify and apply performance improvements
  testing/             — generate test suites for new implementations
  benchmarking/        — measure and compare implementation performance
  deployment/          — containerisation and deployment artefacts
  verification/        — formal or empirical correctness checking

Safety contract: every function in this module must check that its
input hypothesis has review_status == "accepted" before proceeding.
"""


def require_accepted(review_status: str) -> None:
    """Raise ValueError if the hypothesis has not been accepted by a human."""
    if review_status != "accepted":
        raise ValueError(
            f"Research engineering may only operate on accepted hypotheses "
            f"(current status: '{review_status}'). "
            "Have a human reviewer accept this hypothesis first via the /review endpoint."
        )
