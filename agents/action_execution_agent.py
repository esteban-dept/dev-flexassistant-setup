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
        # 1. Define the tools available to this agent (Retrieval Actions)
        # [cite: 131, 132, 133, 134]
        self.tools = [
            get_schedule,
            get_payslip,
            get_contracts,
            get_reservations,
        ]
        
        # 2. Bind the LLM to the tools
        self.llm_with_tools = llm_model.bind_tools(self.tools)
        
        # 3. Define the tool executor
        self.tool_executor = ToolNode(self.tools)
        
        # 4. Base system prompt
        self.system_prompt = system_prompt 

    def run(self, state: AgentState) -> dict:
        """
        Executes the agent logic: Decide Tool -> Execute Tool -> Return Data.
        """
        print("---ACTION EXECUTION AGENT: Starting run()---")
        try:
            # 1. Retrieve Context from State
            # We must inject IDs so the LLM can pass them as arguments to the tools
            c_id = state.get("candidate_id", "unknown")
            e_id = state.get("employee_number", "unknown")
            last_message = state["messages"][-1]
            
            print(f"---Retrieved context: candidate_id={c_id}, employee_number={e_id}---")
            print(f"---Last message: {last_message.content[:100]}...---")

            # 2. Construct Dynamic System Prompt
            # This ensures the agent knows the specific user context for the API calls
            contextualized_prompt = (
                f"{self.system_prompt}\n\n"
                f"CONTEXT DATA:\n"
                f"- Candidate ID: {c_id}\n"
                f"- Employee ID: {e_id}\n"
                "You must pass these IDs to the tools as arguments when required."
            )

            messages = [SystemMessage(content=contextualized_prompt)] + [last_message]
            print(f"---Prepared {len(messages)} messages for LLM---")
            
            # 3. Call LLM to decide on tool usage
            # [cite: 95]
            print("---Calling LLM with tools---")
            agent_response = self.llm_with_tools.invoke(messages)
            print(f"---LLM response received. Tool calls: {len(agent_response.tool_calls) if agent_response.tool_calls else 0}---")
            
            # 4. Check for Tool Call
            if agent_response.tool_calls:
                tool_name = agent_response.tool_calls[0]['name']
                tool_args = agent_response.tool_calls[0].get('args', {})
                print(f"---Executing Tool: {tool_name} with args: {tool_args}---")
                
                # 5. Execute the tool
                # ToolNode expects a dict with 'messages' containing the AI message with tool_calls
                tool_output_response = self.tool_executor.invoke({"messages": [agent_response]})
                print("---Tool execution completed---")
                
                # 6. Extract Result
                # ToolNode returns a list of messages. The last one is the ToolMessage.
                last_tool_message = tool_output_response["messages"][-1]
                
                if isinstance(last_tool_message, ToolMessage):
                    raw_result = last_tool_message.content
                    print(f"---Tool result length: {len(str(raw_result))} characters---")
                    
                    # 7. Update State
                    # We store the raw data in 'retrieved_data' for the AnswerAgent to process
                    # [cite: 103]
                    return {
                        "retrieved_data": raw_result,
                        "error_message": None # Clear previous errors if success
                    }
            
            # Fallback if LLM didn't call a tool when it should have
            print("---No tool called by ActionAgent---")
            return {"error_message": "Agent failed to select a valid tool."}

        except Exception as e:
            # [cite: 156] Supervisor-Level Exception Management
            # Return the error to state so the Supervisor or AnswerAgent can handle it
            print(f"---Error in ActionExecutionAgent: {e}---")
            return {
                "retrieved_data": "",
                "error_message": str(e)
            }