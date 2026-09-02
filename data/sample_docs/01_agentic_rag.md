# Agentic RAG Overview

Agentic Retrieval-Augmented Generation (RAG) combines a large language model
with autonomous decision-making. Instead of always retrieving documents once
and answering, an agent decides *when* and *what* to retrieve, can call multiple
tools, and can reason over intermediate results before responding.

The core loop is the ReAct pattern: the model reasons about the question, takes
an action (such as calling a retrieval tool), observes the result, and repeats
until it can answer confidently. This makes the system robust to questions that
require multiple lookups or a mix of internal knowledge and external search.
