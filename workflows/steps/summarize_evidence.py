import json

import httpx

from workflows.base_step import BaseWorkflowStep, PipelineContext


class SummarizeEvidenceStep(BaseWorkflowStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.retrieved_chunks:
            ctx.evidence_summary = "No relevant papers found in this project for the given question."
            return ctx

        try:
            from app.config import settings
            creds = settings.llm_credentials
            if not creds:
                raise ValueError("No LLM configured")
            base_url, api_key, model = creds

            evidence = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(ctx.retrieved_chunks))
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Summarize the evidence in 3-5 concise sentences."},
                            {"role": "user", "content": f"Evidence:\n{evidence}\n\nQuestion: {ctx.question}"},
                        ],
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                ctx.evidence_summary = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            ctx.evidence_summary = " ".join(ctx.retrieved_chunks[:3])[:1000]

        return ctx
