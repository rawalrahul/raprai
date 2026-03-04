"""
helm/pipeline/ — Task Pipeline & AI Delegation engine.

Decomposes complex tasks into subtasks, assigns each to the best-fit AI,
and orchestrates execution (sequential or parallel) with live UI updates.
"""

from .models import make_pipeline, make_step, pipeline_state_payload
from .planner import plan_pipeline
from .executor import execute_pipeline

__all__ = [
    "make_pipeline", "make_step", "pipeline_state_payload",
    "plan_pipeline", "execute_pipeline",
]
