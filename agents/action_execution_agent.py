import os
import sys
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
        
        # 1. IDEMPOTENCY CHECK
        if state.get("retrieved_data"):
            print("---Data already retrieved. Skipping execution.---")
            return {}

        try:
            # 2. PREPARE CONTEXT
            c_id = state.get("candidate_id", "unknown")
            e_id = state.get("employee_number", "unknown") # Fixed key name
            messages_list = state.get("messages", [])
            
            if not messages_list:
                return {"error_message": "No user message provided."}
            
            last_message = messages_list[-1]
            
            contextualized_prompt = (
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
            # If the LLM somehow returns the tool output directly (rare but possible), use it.
            if hasattr(agent_response, "messages"):
                existing_tool_msgs = [m for m in agent_response.messages if isinstance(m, ToolMessage)]
                if existing_tool_msgs:
                    print("---LLM response already contains tool output. Skipping re-execution.---")
                    return {"retrieved_data": existing_tool_msgs[-1].content, "error_message": None}

            # 5. CHECK FOR TOOL CALLS
            if not agent_response.tool_calls:
                print("---No tool call detected in LLM response---")
                return {"error_message": "Agent did not request a valid tool."}

            # 6. EXECUTE TOOL
            tool_name = agent_response.tool_calls[0]['name']
            print(f"---Executing Tool: {tool_name}---")
            
            tool_output_response = self.tool_executor.invoke({"messages": [agent_response]})
            
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