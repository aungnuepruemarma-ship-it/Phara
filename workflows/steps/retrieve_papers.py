from workflows.base_step import BaseWorkflowStep, PipelineContext


class RetrievePapersStep(BaseWorkflowStep):
    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        from memory.vector_store import search_similar

        results = search_similar(ctx.question, ctx.project_id, top_k=self.top_k)
        ctx.retrieved_chunks = [r.chunk_text for r in results]
        ctx.retrieved_paper_ids = list({r.paper_id for r in results})
        return ctx
