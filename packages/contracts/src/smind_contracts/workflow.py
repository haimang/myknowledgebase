from dataclasses import dataclass


@dataclass
class WorkflowRunContract:
    workflow_run_id: str
    team_id: str
    status: str


@dataclass
class WorkflowStepContract:
    workflow_step_id: str
    workflow_run_id: str
    stage: str
    status: str
