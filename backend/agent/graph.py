from langgraph.graph import StateGraph, END
from typing import Literal

from backend.agent.state import ScraperState
from backend.agent.nodes import observe_node, plan_node, execute_node, correct_node, extract_node

def route_execution(state: ScraperState) -> Literal["observe_node", "correct_node", "extract_node", "failed"]:
    status = state.get("status")
    if status == "running":
        return "observe_node"
    elif status == "correcting":
        return "correct_node"
    elif status == "done":
        return "extract_node"
    return "failed"

def route_correction(state: ScraperState) -> Literal["execute_node", "failed"]:
    if state.get("status") == "failed":
        return "failed"
    return "execute_node"

def route_observe(state: ScraperState) -> Literal["plan_node", "failed"]:
    if state.get("status") == "failed":
        return "failed"
    return "plan_node"

def route_plan(state: ScraperState) -> Literal["execute_node", "failed"]:
    if state.get("status") == "failed":
        return "failed"
    return "execute_node"

def build_graph():
    workflow = StateGraph(ScraperState)

    workflow.add_node("observe_node", observe_node)
    workflow.add_node("plan_node", plan_node)
    workflow.add_node("execute_node", execute_node)
    workflow.add_node("correct_node", correct_node)
    workflow.add_node("extract_node", extract_node)

    workflow.set_entry_point("observe_node")
    workflow.add_conditional_edges(
        "observe_node",
        route_observe,
        {
            "plan_node": "plan_node",
            "failed": END
        }
    )
    
    workflow.add_conditional_edges(
        "plan_node",
        route_plan,
        {
            "execute_node": "execute_node",
            "failed": END
        }
    )

    workflow.add_conditional_edges(
        "execute_node",
        route_execution,
        {
            "observe_node": "observe_node",
            "correct_node": "correct_node",
            "extract_node": "extract_node",
            "failed": END
        }
    )

    workflow.add_conditional_edges(
        "correct_node",
        route_correction,
        {
            "execute_node": "execute_node",
            "failed": END
        }
    )
    workflow.add_edge("extract_node", END)

    return workflow.compile()
