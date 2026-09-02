# LangGraph State Machines

LangGraph models an agent as a directed graph of nodes connected by edges. The
graph carries a typed state object between nodes. A typical ReAct agent has an
"agent" node that calls the language model and a "tools" node that executes any
tool calls the model requested.

Conditional edges route control flow: after the agent node runs, a routing
function inspects the latest message. If the model asked to call a tool, control
moves to the tools node; otherwise the graph terminates and returns the answer.
Because state updates are explicit, LangGraph loops are easy to trace and debug.
