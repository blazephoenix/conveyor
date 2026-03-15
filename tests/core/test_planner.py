import json
from conveyor.core.planner import parse_plan, TaskGraph
from conveyor.tracking.models import RiskLevel


SAMPLE_ORCHESTRATOR_OUTPUT = """
Here is my analysis of the codebase...

The intent requires three tasks.

```
CONVEYOR_PLAN_START
[
  {
    "task_number": 1,
    "title": "Add User model",
    "agent": "backend",
    "files_allowed": ["src/models/user.py"],
    "files_forbidden": ["src/api/*"],
    "depends_on": [],
    "risk": "low",
    "acceptance_criteria": ["User model exists in src/models/user.py"]
  },
  {
    "task_number": 2,
    "title": "Add JWT utilities",
    "agent": "backend",
    "files_allowed": ["src/auth/jwt.py"],
    "files_forbidden": ["src/models/*"],
    "depends_on": [],
    "risk": "low",
    "acceptance_criteria": ["JWT encode/decode functions exist"]
  },
  {
    "task_number": 3,
    "title": "Wire auth endpoints",
    "agent": "backend",
    "files_allowed": ["src/api/auth.py", "src/api/routes.py"],
    "files_forbidden": [],
    "depends_on": [1, 2],
    "risk": "medium",
    "acceptance_criteria": ["/login endpoint works", "/register endpoint works"]
  }
]
CONVEYOR_PLAN_END
```
"""


def test_parse_plan_extracts_tasks():
    graph = parse_plan(SAMPLE_ORCHESTRATOR_OUTPUT)
    assert len(graph.tasks) == 3


def test_parse_plan_task_fields():
    graph = parse_plan(SAMPLE_ORCHESTRATOR_OUTPUT)
    task1 = graph.tasks[0]
    assert task1["title"] == "Add User model"
    assert task1["agent"] == "backend"
    assert task1["risk"] == "low"
    assert task1["depends_on"] == []


def test_parse_plan_dependencies():
    graph = parse_plan(SAMPLE_ORCHESTRATOR_OUTPUT)
    task3 = graph.tasks[2]
    assert task3["depends_on"] == [1, 2]


def test_topological_order():
    graph = parse_plan(SAMPLE_ORCHESTRATOR_OUTPUT)
    order = graph.topological_order()
    # Task 3 depends on 1 and 2, so it must come after both
    indices = {t["task_number"]: i for i, t in enumerate(order)}
    assert indices[3] > indices[1]
    assert indices[3] > indices[2]


def test_parse_plan_bad_output():
    graph = parse_plan("No plan block here at all")
    assert len(graph.tasks) == 0


def test_extract_analysis():
    graph = parse_plan(SAMPLE_ORCHESTRATOR_OUTPUT)
    assert "analysis" in graph.analysis.lower() or len(graph.analysis) > 0
