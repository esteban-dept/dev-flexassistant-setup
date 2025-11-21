from typing import TypedDict, Annotated, List, Union
import os
import sys
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from datetime import datetime

# Ensure parent dir is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from agents.agent_state import AgentState
from agents.action_execution_agent import ActionExecutionAgent

# Load the action execution prompt
prompt_path = os.path.join(parent_dir, "prompts", "action_execution_prompt.txt")
with open(prompt_path, "r") as f:
    action_execution_prompt = f.read()

class ChatSupervisorAgent:
    def __init__(self, model, system_prompt, checkpointer=None):
        self.model = model
        self.system = system_prompt
        
        # Initialize the specialist agent
        self.action_agent_instance = ActionExecutionAgent(
            llm_model=model,
            system_prompt=action_execution_prompt
        ) 

        graph = StateGraph(AgentState)

        # --- 1. Define Nodes ---
        graph.add_node("classify_intent", self.classify_intent_node)
        graph.add_node("action_execution_agent", self.action_agent_instance.run)
        graph.add_node("information_retrieval_agent", self.information_retrieval_agent)
        graph.add_node("fallback_tool", self.fallback_tool)
        graph.add_node("answer_agent", self.answer_agent)

        # --- 2. Define Entry Point ---
        graph.set_entry_point("classify_intent")

        # --- 3. Define Router ---
        graph.add_conditional_edges(
            "classify_intent", 
            self.route_intent, 
            {
                "ActionExecutionAgent": "action_execution_agent",
                "InformationRetrievalAgent": "information_retrieval_agent",
                "FallbackTool": "fallback_tool",
            }
        )

        # --- 4. Define Edges to AnswerAgent ---
        graph.add_edge("action_execution_agent", "answer_agent")
        graph.add_edge("information_retrieval_agent", "answer_agent")
        graph.add_edge("fallback_tool", "answer_agent")
        graph.add_edge("answer_agent", END)

        # 5. Compile
        self.graph = graph.compile(checkpointer=checkpointer)

    def classify_intent_node(self, state: AgentState):
        print("---SUPERVISOR: Classifying Intent---")
        
        # Add current date context to system prompt
        current_date = state.get("date", datetime.now().strftime("%Y-%m-%d"))
        contextualized_system = f"You are an internal agent. Today's date is: {current_date}\n\n{self.system}"
        
        messages = [SystemMessage(content=contextualized_system)] + state['messages']
        response = self.model.invoke(messages)
        intent = response.content.strip()

        valid_routes = ["ActionExecutionAgent", "InformationRetrievalAgent", "FallbackTool"]
        if intent not in valid_routes:
            print(f"Warning: Invalid intent '{intent}'. Defaulting to Fallback.")
            intent = "FallbackTool"

        print(f"Intent: {intent}")
        return {"next_action": intent}

    def route_intent(self, state: AgentState):
        return state["next_action"]

    # --- SPECIALISTS ---
    def information_retrieval_agent(self, state: AgentState):
        print("---Start Information Retrieval Agent---")
        return {"retrieved_data": "Sick leave policy details..."}

    def fallback_tool(self, state: AgentState):
        print("---Start Fallback Tool---")
        return {"error_message": "Could not resolve query."}

    # --- ANSWER AGENT ---
    def answer_agent(self, state: AgentState):
        print("---Start Answer Agent---")
        return {}
