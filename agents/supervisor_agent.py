from typing import TypedDict, Annotated, List, Union
import os
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from agents.agent_state import AgentState
from action_execution_agent import ActionExecutionAgent

import os
import sys
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Load the action execution prompt from the text file
with open(os.path.join(parent_dir, "prompts", "action_execution_prompt.txt"), "r") as f:
    action_execution_prompt = f.read()

class ChatSupervisorAgent:
    def __init__(self, model, system_prompt, checkpointer=None):
        self.model = model
        self.system = system_prompt
        
        self.action_agent_instance = ActionExecutionAgent(
            llm_model=model,
            system_prompt=action_execution_prompt
        ) 

        graph = StateGraph(AgentState)

        # --- 1. Define Nodes ---
        graph.add_node("classify_intent", self.classify_intent_node)
        graph.add_node("action_execution_agent", self.action_agent_instance)
        graph.add_node("information_retrieval_agent", self.information_retrieval_agent)
        graph.add_node("fallback_tool", self.fallback_tool)
        graph.add_node("answer_agent", self.answer_agent) # REQUIRED by architecture

        # --- 2. Define The Entry Point ---
        graph.set_entry_point("classify_intent")

        # --- 3. Define The Conditional Edge (The Router) ---
        graph.add_conditional_edges(
            "classify_intent", 
            self.route_intent, 
            {
                "ActionExecutionAgent": "action_execution_agent",
                "InformationRetrievalAgent": "information_retrieval_agent",
                "FallbackTool": "fallback_tool",
            }
        )

        # --- 4. Define Normal Edges (Enforcing ToV) ---
        graph.add_edge("action_execution_agent", "answer_agent")
        graph.add_edge("information_retrieval_agent", "answer_agent")
        graph.add_edge("fallback_tool", "answer_agent")
        
        # AnswerAgent finishes the run
        graph.add_edge("answer_agent", END)

        # 5. Compile
        self.graph = graph.compile(checkpointer=checkpointer)

    def classify_intent_node(self, state: AgentState):
        '''Reads the user query and classifies the primary action.'''
        messages = [SystemMessage(content=self.system)] + state['messages']
        response = self.model.invoke(messages)
        intent = response.content.strip()

        # Failsafe for valid routing
        valid_routes = ["ActionExecutionAgent", "InformationRetrievalAgent", "FallbackTool"]
        if intent not in valid_routes:
            print(f"Warning: Invalid intent '{intent}'. Defaulting to Fallback.")
            intent = "FallbackTool"

        print(f"Intent classified as: {intent}")
        
        # Return the update to the state
        return {"next_action": intent}

    def route_intent(self, state: AgentState):
        '''Reads the decision made by the intent classifier node'''
        return state["next_action"]

    # --- SPECIALISTS ---

    def information_retrieval_agent(self, state: AgentState):
        '''Retrieves information from the Sharepoint KnowledgeBase'''
        print("---Start Information Retrieval Agent---")
        # Logic to call RAG...
        return {"retrieved_data": "Sick leave policy details..."}

    def fallback_tool(self, state: AgentState):
        print("---Start Fallback Tool---")
        return {"error": "Could not resolve query."}

    # --- ANSWER AGENT (Final Response) ---
    def answer_agent(self, state: AgentState):
        print("---Start Answer Agent---")
        # return {"messages": [AIMessage(content="Final response to user")]}
        