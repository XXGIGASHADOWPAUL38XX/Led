import ast
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def read_led_nodes():
    """List Led nodes with their names and docstring descriptions."""
    nodes = []
    root = Path(__file__).resolve().parent

    for path in sorted(root.rglob("*.py")):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        for cls in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(cls, ast.ClassDef):
                continue
            for statement in cls.body:
                if not isinstance(statement, ast.Assign):
                    continue
                if any(isinstance(t, ast.Name) and t.id == "nodeName" for t in statement.targets):
                    nodes.append({
                        "name": ast.literal_eval(statement.value),
                        "description": ast.get_docstring(cls) or "",
                    })
    return nodes


TOOLS = {"read_led_nodes": read_led_nodes}


def jev(state, questions):
    request = Request(
        "https://opencode.ai/zen/v1/systemone",
        data=json.dumps({
            "model": "jev-1.13",
            "state": state,
            "questions": questions,
        }).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENCODE_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)["answers"]


def agent(question):
    selection = jev(question, {
        "tool": {
            "type": "choice",
            "instructions": "Which tool is needed to answer this question? Choose none if no tool is needed.",
            "criteria": {
                **{name: tool.__doc__ for name, tool in TOOLS.items()},
                "none": "No tool is needed.",
            },
        }
    })["tool"]["choice"]
    state = {"question": question}
    if selection != "none":
        state["tool_result"] = {"tool": selection, "result": TOOLS[selection]()}
    answer = jev(json.dumps(state), {
        "answer": {"type": "noul", "instructions": question}
    })["answer"]["noul"]
    return answer >= 0.5


if __name__ == "__main__":
    print(agent("Does Led have a node for getting the sky color?"))
