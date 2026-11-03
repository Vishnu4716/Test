

import os
import pandas as pd
from datetime import datetime

from lfx.custom import Component
from lfx.io import DataFrameInput, MessageTextInput, StrInput, Output
from lfx.schema import DataFrame


class IncidentReroutingTool(Component):

    display_name = "Incident Rerouting Tool"
    description = (
        "Validates incident reassignment, appends the "
        "rerouting history to a CSV file, and returns a DataFrame."
    )

    icon = "workflow"
    name = "IncidentReroutingTool"

    inputs = [
        DataFrameInput(
            name="incident_dataset",
            display_name="Incident Dataset",
            info="Connect MockDataset_incidents.csv DataFrame."
        ),

        DataFrameInput(
            name="assignment_dataset",
            display_name="Assignment Dataset",
            info="Connect Assignment_data DataFrame."
        ),

        MessageTextInput(
            name="incident_number",
            display_name="Incident Number",
            info="Incident number extracted from user prompt.",
            tool_mode=True
        ),

        MessageTextInput(
            name="target_assignment_group",
            display_name="Target Assignment Group",
            info="Destination group extracted from user prompt.",
            tool_mode=True
        ),

        StrInput(
            name="log_file_path",
            display_name="CSV Log File Path",
            value="Incident_Rerouting_Log.csv",
            info="CSV audit log path inside Langflow runtime."
        )
    ]

    outputs = [
        Output(
            name="rerouting_table",
            display_name="Rerouting DataFrame",
            method="reroute_incident"
        )
    ]

    @staticmethod
    def normalize(value):
        return str(value).strip().casefold()

    def reroute_incident(self) -> DataFrame:

        # STEP 1: Load DataFrames
        incidents = pd.DataFrame(
            self.incident_dataset
        ).copy()

        assignments = pd.DataFrame(
            self.assignment_dataset
        ).copy()

        # STEP 2: Normalize column names
        incidents.columns = [
            str(col).strip().lower()
            for col in incidents.columns
        ]

        assignments.columns = [
            str(col).strip().lower()
            for col in assignments.columns
        ]

        # STEP 3: Extract arguments from Agent
        incident_no = str(
            self.incident_number or ""
        ).strip()

        target_group = str(
            self.target_assignment_group or ""
        ).strip()

        if not incident_no or not target_group:
            raise ValueError(
                "Incident number and target group are required."
            )

        # STEP 4: Validate columns
        required_columns = {
            "number",
            "assignment_group"
        }

        if not required_columns.issubset(
            incidents.columns
        ):
            raise ValueError(
                "Incident DataFrame must contain "
                "number and assignment_group."
            )

        if "assignment_group" not in assignments.columns:
            raise ValueError(
                "Assignment DataFrame must contain "
                "assignment_group."
            )

        # STEP 5: Find incident
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

        if not current_group or current_group.casefold() == "nan":
            raise ValueError(
                "Current assignment group is missing."
            )

        # STEP 6: Validate destination group
        valid_groups = (
            assignments["assignment_group"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        matched_groups = valid_groups[
            valid_groups.str.casefold()
            == self.normalize(target_group)
        ]

        if matched_groups.empty:
            raise ValueError(
                f"Assignment group '{target_group}' does not exist."
            )

        destination_group = matched_groups.iloc[0]

        # STEP 7: Prevent unnecessary reassignment
        if self.normalize(current_group) == self.normalize(
            destination_group
        ):
            raise ValueError(
                f"Incident is already assigned to {current_group}."
            )

        # STEP 8: Create rerouting record
        result = pd.DataFrame([{
            "incident_number": incident_no,
            "rerouted_from": current_group,
            "rerouted_to": destination_group,
            "timestamp": datetime.now().isoformat(timespec="seconds")
        }])

        # STEP 9: Append record to CSV
        log_path = os.path.expanduser(
            str(self.log_file_path).strip()
        )

        if not log_path:
            raise ValueError("CSV log path cannot be empty.")

        log_path = os.path.abspath(log_path)

        os.makedirs(
            os.path.dirname(log_path),
            exist_ok=True
        )

        file_exists = (
            os.path.exists(log_path)
            and os.path.getsize(log_path) > 0
        )

        result.to_csv(
            log_path,
            mode="a",
            header=not file_exists,
            index=False,
            encoding="utf-8"
        )

        # STEP 10: Return DataFrame
        self.status = result

        return DataFrame(result)
