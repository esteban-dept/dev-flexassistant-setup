import os
import sys
parent_dir = os.path.dirname(os.getcwd())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from dotenv import load_dotenv
_ = load_dotenv()

from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langgraph.prebuilt import ToolNode
from datetime import datetime

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
        print(f"---ACTION EXECUTION AGENT: Starting run() [ID: {id(self)}]---")
        
        # 1. IDEMPOTENCY CHECK
        if state.get("retrieved_data"):
            print("---Data already retrieved. Skipping execution.---")
            return {}

        try:
            # 2. PREPARE CONTEXT
            c_id = state.get("candidate_id", "unknown")
            e_id = state.get("employee_number", "unknown")
            current_date = state.get("date", datetime.now().strftime("%Y-%m-%d"))
            messages_list = state.get("messages", [])
            
            if not messages_list:
                return {"error_message": "No user message provided."}
            
            last_message = messages_list[-1]
            print(f"DEBUG: Processing message: {last_message.content[:50]}...")
            
            contextualized_prompt = (
                f"Current date: {current_date}\n\n"
                f"{self.system_prompt}\n\n"
                f"CONTEXT DATA:\n"
                f"- Candidate ID: {c_id}\n"
                f"- Employee ID: {e_id}\n"
                "You must pass these IDs to the tools as arguments."
            )

            # 3. CALL LLM
            print("---Invoking LLM (with tools)---")
            messages = [SystemMessage(content=contextualized_prompt), last_message]
            agent_response = self.llm_with_tools.invoke(messages)
            
            # 4. CHECK FOR EXISTING TOOL OUTPUTS (Avoid Double Execution)
            if hasattr(agent_response, "messages"):
                existing_tool_msgs = [m for m in agent_response.messages if isinstance(m, ToolMessage)]
                if existing_tool_msgs:
                    print("---LLM response already contains tool output. Skipping re-execution.---")
                    return {"retrieved_data": existing_tool_msgs[-1].content, "error_message": None}

            # 5. CHECK FOR TOOL CALLS
            if not agent_response.tool_calls:
                print("---No tool call detected in LLM response---")
                return {"error_message": "Agent did not request a valid tool."}

            # 6. EXECUTE TOOL (SINGLE EXECUTION ENFORCEMENT)
            # We explicitly take only the FIRST tool call to avoid double-execution
            first_tool_call = agent_response.tool_calls[0]
            tool_name = first_tool_call['name']
            print(f"---Executing Tool: {tool_name}---")
            print(f"DEBUG: Tool Args: {first_tool_call.get('args')}")
            
            # Create a sanitized AIMessage containing ONLY the first tool call
            sanitized_msg = AIMessage(
                content="",
                tool_calls=[first_tool_call]
            )
            
            # Invoke ToolNode with the sanitized message
            tool_output_response = self.tool_executor.invoke({"messages": [sanitized_msg]})
            
            # 7. EXTRACT RESULT
            last_tool_message = tool_output_response["messages"][-1]
            content = last_tool_message.content
            
            print(f"---Tool execution completed. Result length: {len(str(content))}---")
            
            return {
                "retrieved_data": str(content),
                "error_message": None
            }

        except Exception as e:
            print(f"---ERROR in ActionExecutionAgent: {e}---")
            return {"error_message": str(e)}