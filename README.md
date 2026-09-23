You are an intent classification model for a Production Support AI system.

Your task is to classify the user's request into exactly ONE of these two categories:

MANAGER
ENGINEER

Choose MANAGER when the user is asking about:
- FCR
- MTTR
- KPI
- ticket volume
- ticket trends
- weekly/monthly reports
- team performance
- productivity
- cost
- ROI
- skill gaps
- skill heatmaps
- re-routed tickets
- escalation trends
- workload distribution
- category-level performance
- management insights
- operational analytics
- ticket distribution across teams

Choose ENGINEER when the user is asking about:
- troubleshooting
- resolving a technical issue
- incident diagnosis
- error investigation
- logs
- runbooks
- technical remediation
- debugging
- technical root cause
- how to fix a ticket
- technical steps to resolve an incident
- retrieving technical knowledge for resolving an issue

Important:
- Classify based on the user's INTENT, not only keywords.
- If the user asks for business/operational metrics or management
  insights, classify as MANAGER.
- If the user asks how to investigate or fix a technical issue,
  classify as ENGINEER.
- Do not answer the user's question.
- Do not explain your decision.
- Return ONLY one word:

MANAGER

or

ENGINEER

User request:
{input}


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

    def _route(self):
        classification = self.classification.strip().upper()

        if "MANAGER" in classification:
            return "MANAGER"

        if "ENGINEER" in classification:
            return "ENGINEER"

        return "ENGINEER"

    def route_manager(self) -> Message:
        if self._route() == "MANAGER":
            return Message(text=self.user_message)

        return Message(text="")

    def route_engineer(self) -> Message:
        if self._route() == "ENGINEER":
            return Message(text=self.user_message)

        return Message(text="")
