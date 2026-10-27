"""Pipeline step ids from the planner AI can't carry script into the page.

The ids go into the pipeline view's onclick="toggleStepDetail('<pipeline>','<step>')".
They came straight from the planner AI's JSON, so an id with a quote in it
would end the string and run whatever followed.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm.pipeline import planner


def test_step_ids_are_cleaned_and_links_kept(monkeypatch):
    plan = {"steps": [
        {"id": "a');alert(1);//", "title": "Fetch", "description": "x", "assigned_ai": "claude"},
        {"id": "step-2", "title": "Write", "description": "y", "assigned_ai": "claude",
         "depends_on": ["a');alert(1);//"]},
        {"id": "<img src=x>", "title": "Odd", "description": "z", "assigned_ai": "claude"},
    ]}
    monkeypatch.setattr(planner, "discover_available_ais", lambda: ["claude"])

    async def fake_planner(ai, prompt, cwd):
        return json.dumps(plan)
    monkeypatch.setattr(planner, "_call_planner_ai", fake_planner)

    pipeline = asyncio.run(planner.plan_pipeline("do it", "s1", "."))
    ids = [s["id"] for s in pipeline["steps"]]
    assert ids == ["aalert1", "step-2", "imgsrcx"]
    assert pipeline["steps"][1]["depends_on"] == ["aalert1"]
