
import pandas as pd

from lfx.custom import Component
from lfx.io import DataFrameInput, MessageTextInput, Output
from lfx.schema import DataFrame


class IncidentReroutingTool(Component):

    display_name = "Incident Rerouting Tool"
    description = (
        "Finds incidents, validates assignment groups, "
        "and creates a tabular rerouting record."
    )
    icon = "workflow"
    name = "IncidentReroutingTool"

    inputs = [
        DataFrameInput(
            name="incident_dataset",
            display_name="Incident Dataset",
            info="Connect the incidents Read File table output."
        ),
        DataFrameInput(
            name="assignment_dataset",
            display_name="Assignment Dataset",
            info="Connect the assignment data Read File table output."
        ),
        MessageTextInput(
            name="incident_number",
            display_name="Incident Number",
            info="Incident number to reroute.",
            tool_mode=True
        ),
        MessageTextInput(
            name="target_assignment_group",
            display_name="Target Assignment Group",
            info="Destination assignment group.",
            tool_mode=True
        )
    ]

    outputs = [
        Output(
            name="rerouting_table",
            display_name="Rerouting Table",
            method="reroute_incident"
        )
    ]

    @staticmethod
    def normalize(value):
        return str(value).strip().casefold()

    def reroute_incident(self) -> DataFrame:

        incidents = pd.DataFrame(self.incident_dataset).copy()
        assignments = pd.DataFrame(self.assignment_dataset).copy()

        # Normalize column headers
        incidents.columns = [
            str(col).strip().lower()
            for col in incidents.columns
        ]

        assignments.columns = [
            str(col).strip().lower()
            for col in assignments.columns
        ]

        incident_no = str(self.incident_number).strip()
        target_group = str(
            self.target_assignment_group
        ).strip()

        if not incident_no or not target_group:
            raise ValueError(
                "Incident number and target group are required."
            )

        # Validate required columns
        if not {"number", "assignment_group"}.issubset(
            incidents.columns
        ):
            raise ValueError(
                "Incident table must contain number and assignment_group."
            )

        if "assignment_group" not in assignments.columns:
            raise ValueError(
                "Assignment table must contain assignment_group."
            )

        # Find incident
        matched_incident = incidents[
            incidents["number"].astype(str).str.strip().str.casefold()
            == self.normalize(incident_no)
        ]

        if matched_incident.empty:
            raise ValueError(
                f"Incident {incident_no} not found."
            )

        current_group = str(
            matched_incident.iloc[0]["assignment_group"]
        ).strip()

        # Validate destination assignment group
        valid_groups = assignments[
            "assignment_group"
        ].dropna().astype(str).str.strip()

        matched_groups = valid_groups[
            valid_groups.str.casefold()
            == self.normalize(target_group)
        ]

        if matched_groups.empty:
            raise ValueError(
                f"Assignment group '{target_group}' does not exist."
            )

        destination_group = matched_groups.iloc[0]

        # Prevent duplicate reassignment
        if self.normalize(current_group) == self.normalize(
            destination_group
        ):
            raise ValueError(
                "Incident is already assigned to this group."
            )

        # Build output table
        rerouting_record = pd.DataFrame([{
            "incident_number": incident_no,
            "rerouted_from": current_group,
            "rerouted_to": destination_group
        }])

        self.status = rerouting_record

        return DataFrame(rerouting_record)
