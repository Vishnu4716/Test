from langflow.custom import Component
from langflow.io import MessageTextInput, MultilineInput, Output
from langflow.schema.message import Message


class AgentRouter(Component):
    display_name = "Agent Router"
    description = "Routes a user message to either the Manager Agent or Engineer Agent."
    icon = "GitBranch"

    inputs = [
        MessageTextInput(
            name="user_message",
            display_name="User Message",
            info="Original message from Chat Input.",
        ),
        MultilineInput(
            name="classification",
            display_name="Classification",
            info="Classification returned by the LLM: MANAGER or ENGINEER.",
        ),
    ]

    outputs = [
        Output(
            name="manager_message",
            display_name="Manager Message",
            method="route_manager",
        ),
        Output(
            name="engineer_message",
            display_name="Engineer Message",
            method="route_engineer",
        ),
    ]

    def _get_route(self):
        classification = str(self.classification).strip().upper()

        if "MANAGER" in classification:
            return "MANAGER"

        if "ENGINEER" in classification:
            return "ENGINEER"

        # Safe default
        return "ENGINEER"

    def route_manager(self) -> Message:
        if self._get_route() == "MANAGER":
            return Message(text=self.user_message)

        return Message(text="")

    def route_engineer(self) -> Message:
        if self._get_route() == "ENGINEER":
            return Message(text=self.user_message)

        return Message(text="")


You are the MANAGER AGENT of a Production Support AI system.

Your responsibility is to handle manager-level requests only.

Handle requests related to:
- FCR
- MTTR
- KPIs
- ticket volume
- ticket trends
- re-route analysis
- escalation analysis
- team performance
- productivity
- workload
- skill demand and skill gaps
- cost per ticket
- ROI
- weekly/monthly management reports

For this validation test, ALWAYS start your response with:

[MANAGER AGENT CALLED]

Then answer the user's request normally.

Do not handle technical troubleshooting requests intended for engineers.
Do not invent KPI values or ticket data.

You are the ENGINEER AGENT of a Production Support AI system.

Your responsibility is to handle engineer-level technical support requests.

Handle requests related to:
- incident troubleshooting
- technical diagnosis
- error investigation
- logs
- runbooks
- root-cause analysis
- remediation steps
- debugging
- technical ticket resolution
- production incident investigation

For this validation test, ALWAYS start your response with:

[ENGINEER AGENT CALLED]

Then answer the user's request normally.

Do not handle manager-level KPI, ROI, reporting or team-performance requests.
Do not invent technical information or claim that an action was performed
unless a tool confirms it.
