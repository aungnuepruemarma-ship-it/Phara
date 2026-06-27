from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent

BIO_KEYWORDS = frozenset([
    "gene", "protein", "dna", "rna", "cell", "organism", "evolution",
    "mutation", "genome", "sequence", "expression", "pathway", "enzyme",
    "metabolism", "neural", "brain", "cognition", "disease", "cancer",
    "drug", "immune", "virus", "bacteria", "ecology", "population",
    "phylogeny", "crispr", "epigenetic", "receptor", "membrane",
    "mitochondria", "chromosome", "allele", "phenotype", "genotype",
])


class BiologyAgent(LLMAgent):
    """Specialist agent for biology and life sciences research."""

    name = "biology_research_agent"
    description = "Specializes in molecular biology, genetics, neuroscience, and life sciences."

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        prompt = (
            "You are an expert biological research assistant with deep knowledge spanning "
            "molecular biology, genetics, evolutionary biology, neuroscience, and medicine."
        )
        lower = input_data.question.lower()
        if any(kw in lower for kw in ("gene", "dna", "rna", "crispr", "genome", "expression")):
            prompt += (
                " Apply molecular biology rigor: cite specific mechanisms, pathways, "
                "and experimental evidence from the literature."
            )
        elif any(kw in lower for kw in ("brain", "neural", "cognition", "neuron")):
            prompt += " Apply neuroscience principles, distinguishing between circuit-level and molecular mechanisms."
        return prompt

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        lower = input_data.question.lower()
        detected = [kw for kw in BIO_KEYWORDS if kw in lower]
        return {"domain": "biology", "detected_topics": detected}
