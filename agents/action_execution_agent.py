import os
import sys
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from dotenv import load_dotenv
_ = load_dotenv()

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_openai import AzureChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.runnables import Runnable
from langgraph.prebuilt import ToolNode

from agents.agent_state import AgentState

from tools.GetPayslipTool import get_payslip
from tools.GetReservationsTool import get_reservations
from tools.GetContractsTool import get_contracts
from tools.GetScheduleTool import get_schedule

# Load the action execution prompt from the text file
with open(os.path.join(parent_dir, "prompts", "action_execution_prompt.txt"), "r") as f:
    action_execution_prompt = f.read()

from agents.llm_model import AzureModelProvider
provider = AzureModelProvider()
llm = provider.get_primary_model()

# ------------------------

class ActionExecutionAgent:
    def __init__(self, llm_model, system_prompt):
        # 1. Define the tools available to this agent
        self.tools = [
            get_schedule,
            get_payslip,
            get_contracts,
            get_reservations,
        ]
        
        # 2. Bind the LLM to the tools for function calling
        #    This allows the model to return a structured 'tool_call' object
        self.llm_with_tools: Runnable = llm_model.bind_tools(self.tools)
        # 3. Define the tool executor
        #    This component handles executing the tool calls requested by the LLM
        self.tool_executor = ToolNode(self.tools)
        # 4. Agent's system prompt (for reasoning/tool selection)
        self.system_prompt = system_prompt 

    def run(self, state: AgentState) -> dict:
        """
        The method executed as the LangGraph node. It acts as the agent loop.
        """
        # 1. Get the latest message (the specific personalized request)
        last_message = state["messages"][-1]
        print("1. last_message: ", last_message)
        
        # 2. Add the agent's specific system prompt to the call
        #    This prompt guides the agent to select and execute the single best tool
        messages = [SystemMessage(content=self.system_prompt)] + [last_message]
        print("2. messages: ", messages)
        
        # 3. Call the LLM to decide on the tool and parameters
        agent_response = self.llm_with_tools.invoke(messages)
        print("3. agent_response:", agent_response)
        # 4. Check for tool call
        if agent_response.tool_calls:
            # 5. Execute the tool directly using ToolNode
            #    ToolNode can handle the agent_response with tool_calls directly
            tool_output = self.tool_executor.invoke({"messages": [agent_response]})
            print("5. tool_output:", tool_output)
            
            # 6. Extract the actual tool result from the tool message
            if tool_output and "messages" in tool_output:
                tool_result = tool_output["messages"][-1].content
                return {"retrieved_data": tool_result}
            
            print("6. tool_result:", tool_result)
            # 7. Update state with data
            return {"retrieved_data": str(tool_output)}
            # 7. Update state with data
            return {"retrieved_data": str(tool_output)}
            # Failsafe: If the agent hallucinates or refuses to use a tool, route to Fallback
            return {"error": "Agent failed to execute tool call."}