from eeg_core.workflow.schema import WorkflowSpec


def describe_workflow(spec: WorkflowSpec) -> dict:
    return {"id": spec.id, "name": spec.name, "steps": [step.model_dump() for step in spec.steps]}

