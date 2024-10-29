from typing import TypedDict, List, Dict, Union

class SessionState(TypedDict):
    user_id: str
    messages: List
    current_filter: Dict[str, List[str]]
    action: Union[str]
    recommendations: List
    current_recommendation: int


def update_state(state: SessionState, state_update: dict):
    for key, value in state_update.items():
        if key == "messages":
            state["messages"].append(value)
        else:
            state[key] = value

    return state