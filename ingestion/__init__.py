"""ingestion — import, normalise, and index knowledge from multiple sources.

Sub-packages:
  pdf/              — PDF text extraction (wraps tools/pdf_parser)
  academic/         — arXiv, Semantic Scholar, PubMed, CrossRef importers
  datasets/         — structured dataset loaders
  code/             — GitHub repository and snippet ingestion
  documents/        — generic document pipeline (markdown, text, html)
  cleaner/          — whitespace, encoding, PII scrubbing
  normalizer/       — sentence splitting, schema normalisation
  entity_extractor/ — extract named entities from ingested text
  citation_parser/  — parse reference lists and DOI resolution
"""
