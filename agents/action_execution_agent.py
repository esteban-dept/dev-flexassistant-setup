import os
import sys
import json
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from dotenv import load_dotenv
_ = load_dotenv()

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from agents.agent_state import AgentState

from tools.GetPayslipTool import get_payslip
from tools.GetReservationsTool import get_reservations
from tools.GetContractsTool import get_contracts
from tools.GetScheduleTool import get_schedule

# ------------------------


class ActionExecutionAgent:
    def __init__(self, llm_model, system_prompt):
        self.tools = [
            get_schedule,
            get_payslip,
            get_contracts,
            get_reservations,
        ]
        self.llm_with_tools = llm_model.bind_tools(self.tools)
        self.tool_executor = ToolNode(self.tools)
        self.system_prompt = system_prompt 

    def run(self, state: AgentState) -> dict:
        print("---ACTION EXECUTION AGENT: Starting run()---")
        
        # --- 1. IDEMPOTENCY CHECK 
        if state.get("retrieved_data"):
            print("---Data already retrieved. Skipping execution.---")
            return {}

        try:
            # 2. Prepare Context
            c_id = state.get("candidate_id", "unknown")
            e_id = state.get("employee_id", "unknown")
            last_message = state["messages"][-1]
            
            print(f"---Retrieved context: candidate_id={c_id}, employee_id={e_id}---")
            print(f"---Last message type: {type(last_message).__name__}---")
            print(f"---Last message content: {last_message.content[:100]}...---")

            contextualized_prompt = (
                f"{self.system_prompt}\n\n"
                f"CONTEXT DATA:\n"
                f"- Candidate ID: {c_id}\n"
                f"- Employee ID: {e_id}\n"
                "You must pass these IDs to the tools as arguments."
            )

            messages = [SystemMessage(content=contextualized_prompt)] + [last_message]
            print(f"---Prepared {len(messages)} messages for LLM---")
            print(f"---System prompt length: {len(contextualized_prompt)} characters---")
            
            # 3. Invoke LLM
            print("---Calling LLM with tools---")
            agent_response = self.llm_with_tools.invoke(messages)
            print(f"---LLM response received---")
            print(f"---Response type: {type(agent_response).__name__}---")
            print("agent_response.tool_calls:", agent_response.tool_calls)
            print(f"---Tool calls count: {len(agent_response.tool_calls) if agent_response.tool_calls else 0}---")
            
            # 4. Handle Tool Calls
            if agent_response.tool_calls:
                tool_name = agent_response.tool_calls[0]['name']
                tool_args = agent_response.tool_calls[0].get('args', {})
                print(f"---Executing Tool: {tool_name}---")
                print(f"---Tool arguments: {tool_args}---")
                
                # Execute Tool
                print("---Invoking tool executor---")
                tool_output_response = self.tool_executor.invoke({"messages": [agent_response]})
                print(f"---Tool executor response received---")
                print(f"---Tool output messages count: {len(tool_output_response.get('messages', []))}---")
                
                last_tool_message = tool_output_response["messages"][-1]
                print(f"---Last tool message type: {type(last_tool_message).__name__}---")
                
                if isinstance(last_tool_message, ToolMessage):
                    result_length = len(str(last_tool_message.content))
                    print(f"---Tool execution completed. Result length: {result_length} characters---")
                    print(f"---Tool result preview: {str(last_tool_message.content)[:200]}...---")
                    return {
                        "retrieved_data": last_tool_message.content,
                        "error_message": None
                    }
                else:
                    print(f"---Unexpected tool message type: {type(last_tool_message)}---")
            
            print("---No tool called by LLM---")
            return {"error_message": "Agent failed to select a valid tool."}

        except Exception as e:
            print(f"---Error in ActionExecutionAgent: {e}---")
            print(f"---Error type: {type(e).__name__}---")
            import traceback
            print(f"---Full traceback: {traceback.format_exc()}---")
            return {"error_message": str(e)}