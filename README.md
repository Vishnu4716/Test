from typing import Any

import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import (
    DataFrameInput,
    MessageTextInput,
    Output,
)
from lfx.field_typing import Data
from lfx.schema import DataFrame


class IncidentHeatmapComponent(Component):
    """
    Incident Heatmap Generator

    Reads ticket/incident data from a connected Read File component,
    calculates incident counts by assignment group and state,
    estimates engineer demand, and exposes the component as an Agent tool.
    """

    display_name = "Incident Heatmap Generator"

    description = (
        "Generates an incident/skill demand heatmap from ticket data. "
        "Can be connected to a Read File DataFrame and also exposed "
        "as a tool for an Agent."
    )

    documentation = (
        "https://docs.langflow.org/components-custom-components"
    )

    icon = "chart-bar"

    name = "IncidentHeatmap"

    # ============================================================
    # INPUTS
    # ============================================================

    inputs = [

        # --------------------------------------------------------
        # NORMAL DATAFRAME INPUT
        # --------------------------------------------------------
        DataFrameInput(
            name="connected_data",
            display_name="Ticket Data",
            info=(
                "Connect the DataFrame output from Read File here. "
                "Required columns: assignment_group and state."
            ),
            required=False,
        ),

        # --------------------------------------------------------
        # TOOL INPUT
        # --------------------------------------------------------
        MessageTextInput(
            name="tool_request",
            display_name="Analysis Request",
            info=(
                "Used when this component is called as a tool by the "
                "Manager Agent. The connected Ticket Data will be analyzed."
            ),
            value="Generate the incident skill-demand heatmap.",
            tool_mode=True,
            required=False,
        ),
    ]

    # ============================================================
    # OUTPUTS
    # ============================================================

    outputs = [

        Output(
            display_name="Heatmap Output",
            name="heatmap_output",
            method="generate_heatmap",
        ),
    ]

    # ============================================================
    # HARD-CODED ENGINEER COUNTS
    # ============================================================

    ENGINEER_COUNTS = {
        "Network Operations": 5,
        "Service Desk": 4,
        "Identity And Access": 8,
        "Database Platform": 3,
        "Messaging Services": 4,
        "End User Computing": 6,
        "Core Infrastructure": 3,
        "Business Applications": 9,
        "Identity Engineering": 2,
        "Platform Engineering": 5,
    }

    # ============================================================
    # HELPER
    # ============================================================

    @staticmethod
    def _demand_level(
        tickets_per_engineer: float,
    ) -> str:

        if tickets_per_engineer > 20:
            return "High"

        if tickets_per_engineer > 10:
            return "Medium"

        return "Low"

    # ============================================================
    # DATA EXTRACTION
    # ============================================================

    def _get_dataframe(self) -> pd.DataFrame:
        """
        Gets the DataFrame from the normal Read File connection.

        The Agent tool uses the same connected DataFrame.
        """

        input_data = getattr(
            self,
            "connected_data",
            None,
        )

        if input_data is None:
            raise ValueError(
                "No ticket data is connected. "
                "Connect the Read File DataFrame output "
                "to the 'Ticket Data' input."
            )

        # --------------------------------------------------------
        # Langflow Data wrapper
        # --------------------------------------------------------

        if hasattr(input_data, "value"):

            value = input_data.value

            if isinstance(value, pd.DataFrame):
                return value.copy()

        # --------------------------------------------------------
        # Direct pandas DataFrame
        # --------------------------------------------------------

        if isinstance(
            input_data,
            pd.DataFrame,
        ):
            return input_data.copy()

        # --------------------------------------------------------
        # Langflow Data object may contain dataframe in .data
        # --------------------------------------------------------

        if hasattr(input_data, "data"):

            data = input_data.data

            if isinstance(data, pd.DataFrame):
                return data.copy()

            if isinstance(data, dict):

                for key in [
                    "dataframe",
                    "df",
                    "value",
                ]:

                    value = data.get(key)

                    if isinstance(
                        value,
                        pd.DataFrame,
                    ):
                        return value.copy()

        raise ValueError(
            "The connected input is not a pandas DataFrame. "
            "Connect the DataFrame output from Read File."
        )

    # ============================================================
    # CORE HEATMAP LOGIC
    # ============================================================

    def _build_heatmap(
        self,
        df: pd.DataFrame,
    ) -> Data:

        # --------------------------------------------------------
        # 1. Validate columns
        # --------------------------------------------------------

        required_columns = {
            "assignment_group",
            "state",
        }

        missing = (
            required_columns
            - set(df.columns)
        )

        if missing:

            raise ValueError(
                "Missing required column(s): "
                + ", ".join(sorted(missing))
            )

        # --------------------------------------------------------
        # 2. Work on a copy
        # --------------------------------------------------------

        df = df.copy()

        # --------------------------------------------------------
        # 3. Normalize values
        # --------------------------------------------------------

        df["assignment_group"] = (
            df["assignment_group"]
            .astype(str)
            .str.strip()
            .str.title()
        )

        df["state"] = (
            df["state"]
            .astype(str)
            .str.strip()
            .str.title()
        )

        # --------------------------------------------------------
        # 4. Count incidents by skill + state
        # --------------------------------------------------------

        skill_status_counts = (
            df
            .groupby(
                [
                    "assignment_group",
                    "state",
                ]
            )
            .size()
            .unstack(
                fill_value=0
            )
        )

        # --------------------------------------------------------
        # 5. Total tickets
        # --------------------------------------------------------

        skill_status_counts[
            "Total"
        ] = (
            skill_status_counts
            .sum(axis=1)
        )

        # --------------------------------------------------------
        # 6. Engineer counts
        # --------------------------------------------------------

        skill_status_counts[
            "Engineers"
        ] = (
            skill_status_counts
            .index
            .map(
                lambda group:
                    self.ENGINEER_COUNTS.get(
                        group,
                        1,
                    )
            )
            .astype(int)
        )

        # --------------------------------------------------------
        # 7. Tickets per engineer
        # --------------------------------------------------------

        skill_status_counts[
            "Tickets/Engineer"
        ] = (
            skill_status_counts["Total"]
            / skill_status_counts["Engineers"]
        ).round(2)

        # --------------------------------------------------------
        # 8. Demand level
        # --------------------------------------------------------

        skill_status_counts[
            "Demand Level"
        ] = (
            skill_status_counts[
                "Tickets/Engineer"
            ]
            .apply(
                self._demand_level
            )
        )

        # --------------------------------------------------------
        # 9. Final table
        # --------------------------------------------------------

        result_df = (
            skill_status_counts
            .reset_index()
        )

        # Rename assignment group
        result_df = result_df.rename(
            columns={
                "assignment_group":
                    "Skill / Competency",

                "Total":
                    "Total Tickets",

                "Engineers":
                    "Engineers",

                "Tickets/Engineer":
                    "Tickets / Engineer",

                "Demand Level":
                    "Demand Level",
            }
        )

        # --------------------------------------------------------
        # 10. Sort by ticket volume
        # --------------------------------------------------------

        result_df = result_df.sort_values(
            "Total Tickets",
            ascending=False,
        )

        # --------------------------------------------------------
        # 11. Markdown output
        # --------------------------------------------------------

        markdown_table = (
            result_df
            .to_markdown(
                index=False
            )
        )

        # Add summary
        total_tickets = len(df)

        total_engineers = sum(
            self.ENGINEER_COUNTS.get(
                group,
                1,
            )
            for group in df[
                "assignment_group"
            ].unique()
        )

        high_demand_count = (
            result_df[
                "Demand Level"
            ]
            .eq("High")
            .sum()
        )

        summary = f"""
## Incident Skill-Demand Heatmap

**Total incidents:** {total_tickets}

**Skills / Assignment Groups:** {len(result_df)}

**Estimated engineers represented:** {total_engineers}

**High-demand skill groups:** {high_demand_count}

### Skill Demand

{markdown_table}
"""

        self.status = (
            f"Generated heatmap for "
            f"{total_tickets} incidents."
        )

        return Data(
            value=summary
        )

    # ============================================================
    # OUTPUT / TOOL ACTION
    # ============================================================

    def generate_heatmap(self) -> Data:
        """
        Generates the heatmap.

        This method works both when:
        1. The component is executed normally, and
        2. The component is called by the Manager Agent as a tool.
        """

        df = self._get_dataframe()

        return self._build_heatmap(
            df
        )
