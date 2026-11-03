
import csv
import json
import os
from io import StringIO
from datetime import datetime, timezone

from lfx.custom import Component
from lfx.io import DataInput, MessageTextInput, StrInput, Output
from lfx.schema import Data


class IncidentReroutingTool(Component):

    display_name = "Incident Rerouting Tool"
    description = (
        "Validates an incident and destination assignment group, "
        "then records the reassignment history."
    )
    icon = "workflow"
    name = "IncidentReroutingTool"

    inputs = [
        DataInput(
            name="incident_dataset",
            display_name="Incident Dataset",
            info="Connect Read File output for MockDataset_incidents.csv."
        ),
        DataInput(
            name="assignment_dataset",
            display_name="Assignment Dataset",
            info="Connect Read File output for Assignment_data.csv."
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
        ),
        StrInput(
            name="log_file_path",
            display_name="Rerouting Log Path",
            value="Incident_Rerouting_Log.json",
            info="Path where reassignment history is stored."
        )
    ]

    outputs = [
        Output(
            name="result",
            display_name="Rerouting Result",
            method="reroute_incident"
        )
    ]

    def _get_csv_text(self, source):

        if source is None:
            raise ValueError("Dataset input is empty.")

        # Handle Langflow Data objects
        if hasattr(source, "data"):
            source = source.data

        # Handle dictionaries returned by components
        if isinstance(source, dict):
            for key in ("content", "raw_content", "text"):
                if key in source:
                    source = source[key]
                    break

        # Handle message-like objects
        if hasattr(source, "text"):
            source = source.text

        if isinstance(source, bytes):
            source = source.decode("utf-8-sig")

        # Handle DataFrame-like objects
        if hasattr(source, "to_csv"):
            source = source.to_csv(index=False)

        if not isinstance(source, str):
            raise TypeError(
                "Expected CSV text from Read File. "
                "Export Excel files as CSV before connecting."
            )

        return source.lstrip("\ufeff")

    def _read_csv(self, source):

        content = self._get_csv_text(source)

        reader = csv.DictReader(StringIO(content))

        if not reader.fieldnames:
            raise ValueError("CSV file has no headers.")

        # Normalize header names
        rows = []

        for row in reader:
            normalized = {
                str(key).strip().lower(): (
                    value.strip() if isinstance(value, str) else value
                )
                for key, value in row.items()
                if key is not None
            }
            rows.append(normalized)

        return rows

    def _normalize(self, value):
        return str(value or "").strip().casefold()

    def reroute_incident(self) -> Data:

        try:
            incident_no = str(self.incident_number or "").strip()
            target_group = str(
                self.target_assignment_group or ""
            ).strip()

            if not incident_no or not target_group:
                raise ValueError(
                    "Incident number and target assignment group are required."
                )

            # STEP 1: Read incident dataset
            incidents = self._read_csv(self.incident_dataset)

            # STEP 2: Find requested incident
            incident = next(
                (
                    row for row in incidents
                    if self._normalize(row.get("number")) ==
                    self._normalize(incident_no)
                ),
                None
            )

            if incident is None:
                raise ValueError(
                    f"Incident {incident_no} was not found."
                )

            # STEP 3: Extract current assignment group
            current_group = incident.get("assignment_group", "")

            if not current_group:
                raise ValueError(
                    "Current assignment group is missing in incident data."
                )

            # STEP 4: Read assignment dataset
            assignments = self._read_csv(self.assignment_dataset)

            # STEP 5: Validate destination group
            valid_groups = [
                row.get("assignment_group", "")
                for row in assignments
            ]

            matched_group = next(
                (
                    group for group in valid_groups
                    if self._normalize(group) ==
                    self._normalize(target_group)
                ),
                None
            )

            if not matched_group:
                raise ValueError(
                    f"Assignment group '{target_group}' "
                    "does not exist in Assignment_data."
                )

            # STEP 6: Prevent unnecessary reassignment
            if self._normalize(current_group) == self._normalize(
                matched_group
            ):
                raise ValueError(
                    f"Incident {incident_no} is already assigned "
                    f"to {current_group}."
                )

            # STEP 7: Prepare audit record
            record = {
                "incident_number": incident_no,
                "rerouted_from": current_group,
                "rerouted_to": matched_group,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            # STEP 8: Append to JSON log
            log_path = os.path.expanduser(
                str(self.log_file_path).strip()
            )

            if not log_path:
                raise ValueError("Rerouting log path is empty.")

            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as file:
                    history = json.load(file)

                if not isinstance(history, list):
                    raise ValueError(
                        "Rerouting log must contain a JSON list."
                    )
            else:
                history = []

            history.append(record)

            directory = os.path.dirname(
                os.path.abspath(log_path)
            )
            os.makedirs(directory, exist_ok=True)

            with open(log_path, "w", encoding="utf-8") as file:
                json.dump(history, file, indent=4)

            self.status = (
                f"Incident {incident_no} rerouted successfully."
            )

            return Data(data={
                "status": "success",
                **record,
                "message": (
                    f"Incident {incident_no} successfully rerouted "
                    f"from {current_group} to {matched_group}."
                )
            })

        except Exception as error:

            self.status = f"Rerouting failed: {str(error)}"

            return Data(data={
                "status": "failed",
                "message": str(error)
            })
