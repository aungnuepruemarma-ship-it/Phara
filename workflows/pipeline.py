from workflows.base_step import BaseWorkflowStep, PipelineContext


class ResearchPipeline:
    def __init__(self, steps: list[BaseWorkflowStep]):
        self.steps = steps

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        for step in self.steps:
            ctx = await step.execute(ctx)
        return ctx
