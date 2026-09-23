from typing import Any

from lfx.base.models.unified_models import (

    get_llm,

    handle_model_input_update,

)

from lfx.custom import Component

from lfx.io import (

    BoolInput,

    MessageInput,

    MessageTextInput,

    ModelInput,

    MultilineInput,

    Output,

    SecretStrInput,

    TableInput,

)

from lfx.schema.message import Message

class SmartRouterComponent(Component):

    display_name = "Smart Router"

    description = (

        "LLM-based router for Production Support Manager and Engineer requests."

    )

    icon = "route"

    name = "SmartRouter"

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self._categorization_result = None

        self._matched_category = None

        self._excluded_outputs = set()

    # ---------------------------------------------------------

    # INPUTS

    # ---------------------------------------------------------

    inputs = [

        ModelInput(

            name="model",

            display_name="Language Model",

            info="LLM used to classify the user's request.",

            real_time_refresh=True,

            required=True,

        ),

        SecretStrInput(

            name="api_key",

            display_name="API Key",

            info="Optional API key. Leave blank if the environment already provides it.",

            real_time_refresh=True,

            advanced=True,

        ),

        MessageTextInput(

            name="input_text",

            display_name="Input",

            info="Original user message to route.",

            required=True,

        ),

        TableInput(

            name="routes",

            display_name="Routes",

            info="Routing categories for Manager and Engineer.",

            table_schema=[

                {

                    "name": "route_category",

                    "display_name": "Route Name",

                    "type": "str",

                    "description": "Exact route name.",

                },

                {

                    "name": "route_description",

                    "display_name": "Route Description",

                    "type": "str",

                    "description": "Description used by the LLM to choose the route.",

                },

                {

                    "name": "output_value",

                    "display_name": "Route Message",

                    "type": "str",

                    "description": "Optional replacement message. Leave EMPTY to pass original input.",

                    "default": "",

                },

            ],

            value=[

                {

                    "route_category": "MANAGER",

                    "route_description": (

                        "Production support management requests including FCR, MTTR, "

                        "KPIs, ticket volume, ticket trends, weekly or monthly reports, "

                        "team performance, productivity, workload, cost, ROI, skill gaps, "

                        "re-routing, escalations, ticket distribution and operational analytics."

                    ),

                    "output_value": "",

                },

                {

                    "route_category": "ENGINEER",

                    "route_description": (

                        "Production support technical requests including troubleshooting, "

                        "incident diagnosis, technical errors, logs, runbooks, debugging, "

                        "root-cause analysis, remediation and resolving production incidents."

                    ),

                    "output_value": "",

                },

            ],

            real_time_refresh=True,

            required=True,

        ),

        MessageInput(

            name="message",

            display_name="Override Output",

            info="Optional testing override. Leave empty during normal use.",

            required=False,

            advanced=True,

        ),

        BoolInput(

            name="enable_else_output",

            display_name="Include Else Output",

            info="Enable only if you want an Else branch for unmatched requests.",

            value=False,

            advanced=True,

            real_time_refresh=True,

        ),

        MultilineInput(

            name="custom_prompt",

            display_name="Additional Instructions",

            info="Optional additional instructions for the routing LLM.",

            advanced=True,

        ),

    ]

    # Outputs are created dynamically from the Routes table.

    outputs: list[Output] = []

    # ---------------------------------------------------------

    # DYNAMIC OUTPUT CREATION

    # ---------------------------------------------------------

    def update_build_config(

        self,

        build_config: dict,

        field_value: str,

        field_name: str | None = None,

    ):

        return handle_model_input_update(

            self,

            build_config,

            field_value,

            field_name,

        )

    def update_outputs(

        self,

        frontend_node: dict,

        field_name: str,

        field_value: Any,

    ) -> dict:

        """

        Dynamically creates one output for every route.

        Example:

            MANAGER

            ENGINEER

        """

        if field_name in {"routes", "enable_else_output", "model"}:

            frontend_node["outputs"] = []

            routes_data = (

                field_value

                if field_name == "routes"

                else getattr(self, "routes", [])

            )

            if not routes_data:

                routes_data = []

            for index, row in enumerate(routes_data):

                route_name = str(

                    row.get(

                        "route_category",

                        f"Category {index + 1}",

                    )

                ).strip()

                if not route_name:

                    route_name = f"Category {index + 1}"

                safe_name = "".join(

                    char if char.isalnum() else "_"

                    for char in route_name

                )

                frontend_node["outputs"].append(

                    Output(

                        display_name=route_name,

                        name=f"category_{index + 1}_{safe_name}",

                        method="process_case",

                        group_outputs=True,

                    )

                )

            if getattr(

                self,

                "enable_else_output",

                False,

            ):

                frontend_node["outputs"].append(

                    Output(

                        display_name="Else",

                        name="default_result",

                        method="default_response",

                        group_outputs=True,

                    )

                )

        return frontend_node

    # ---------------------------------------------------------

    # ROUTING / CLASSIFICATION

    # ---------------------------------------------------------

    def _get_categorization(self) -> str:

        if self._categorization_result is not None:

            return self._categorization_result

        routes = getattr(self, "routes", []) or []

        input_text = getattr(self, "input_text", "") or ""

        if not routes:

            self.status = "No routes configured."

            self._categorization_result = "NONE"

            return self._categorization_result

        llm = get_llm(

            model=self.model,

            user_id=self.user_id,

            api_key=self.api_key,

        )

        if not llm:

            self.status = "Language Model unavailable."

            self._categorization_result = "NONE"

            return self._categorization_result

        # Build route descriptions for the LLM.

        route_lines = []

        for index, route in enumerate(routes):

            route_name = route.get(

                "route_category",

                f"Category {index + 1}",

            )

            route_description = route.get(

                "route_description",

                "",

            )

            route_lines.append(

                f"{route_name}: {route_description}"

            )

        routes_text = "\n".join(route_lines)

        prompt = f"""

You are an intent classification router for a Production Support AI system.

Classify the user's request into EXACTLY ONE of these routes:

{routes_text}

Rules:

MANAGER:

- KPI questions

- FCR

- MTTR

- ticket volume

- ticket trends

- management reports

- team performance

- productivity

- workload

- cost

- ROI

- skill demand

- skill gaps

- re-routing analysis

- escalation analysis

- ticket distribution

- operational analytics

- management recommendations

ENGINEER:

- troubleshooting

- production incidents

- technical errors

- logs

- runbooks

- debugging

- root-cause analysis

- technical diagnosis

- remediation

- fixing technical issues

- technical ticket resolution

Classify based on the user's INTENT, not merely keywords.

If the user wants to understand operational performance or management

metrics, choose MANAGER.

If the user wants to investigate or fix a technical issue, choose ENGINEER.

Return ONLY the exact route name.

User request:

{input_text}

Route:

"""

        custom_prompt = getattr(

            self,

            "custom_prompt",

            "",

        )

        if custom_prompt and custom_prompt.strip():

            prompt += f"""

Additional routing instructions:

{custom_prompt}

"""

        try:

            if hasattr(llm, "invoke"):

                response = llm.invoke(prompt)

                if hasattr(response, "content"):

                    category = response.content

                else:

                    category = str(response)

            else:

                response = llm(prompt)

                category = str(response)

            category = (

                category

                .strip()

                .strip('"')

                .strip("'")

            )

            # Match the LLM response against the configured route names.

            matched_category = None

            for route in routes:

                route_name = str(

                    route.get(

                        "route_category",

                        "",

                    )

                ).strip()

                if category.lower() == route_name.lower():

                    matched_category = route_name

                    break

            # If LLM returned extra text, search for exact route name.

            if matched_category is None:

                for route in routes:

                    route_name = str(

                        route.get(

                            "route_category",

                            "",

                        )

                    ).strip()

                    if route_name.lower() in category.lower():

                        matched_category = route_name

                        break

            if matched_category is None:

                self.status = (

                    f"LLM returned an unknown route: {category}"

                )

                self._categorization_result = "NONE"

            else:

                self.status = (

                    f"Routed to {matched_category}"

                )

                self._categorization_result = matched_category

        except Exception as exc:

            self.status = (

                f"Routing error: {exc}"

            )

            self._categorization_result = "NONE"

        return self._categorization_result

    # ---------------------------------------------------------

    # OUTPUT NAME

    # ---------------------------------------------------------

    def _get_output_name(

        self,

        index: int,

        route_name: str,

    ) -> str:

        safe_name = "".join(

            char if char.isalnum() else "_"

            for char in route_name

        )

        return f"category_{index + 1}_{safe_name}"

    # ---------------------------------------------------------

    # BRANCH DEACTIVATION

    # ---------------------------------------------------------

    def _deactivate_branches(

        self,

        names: list[str],

    ) -> None:

        for name in names:

            self._excluded_outputs.add(name)

        try:

            if self._vertex:

                self._vertex.graph.exclude_branches_conditionally(

                    self._id,

                    sorted(self._excluded_outputs),

                )

        except Exception:

            # Branch exclusion is an optimization.

            # Routing still works correctly without it.

            pass

    # ---------------------------------------------------------

    # PRE-RUN

    # ---------------------------------------------------------

    def _pre_run_setup(self) -> None:

        self._categorization_result = None

        self._matched_category = None

        self._excluded_outputs = set()

    # ---------------------------------------------------------

    # MAIN OUTPUT

    # ---------------------------------------------------------

    def process_case(self) -> Message:

        routes = getattr(

            self,

            "routes",

            [],

        ) or []

        input_text = getattr(

            self,

            "input_text",

            "",

        ) or ""

        categorization = self._get_categorization()

        # -----------------------------------------------------

        # Find selected route

        # -----------------------------------------------------

        matched_index = None

        for index, route in enumerate(routes):

            route_name = str(

                route.get(

                    "route_category",

                    "",

                )

            ).strip()

            if (

                categorization.lower()

                == route_name.lower()

            ):

                matched_index = index

                break

        # -----------------------------------------------------

        # No route found

        # -----------------------------------------------------

        if matched_index is None:

            self.status = (

                "No matching route."

            )

            return Message(text="")

        matched_route = routes[matched_index]

        matched_route_name = str(

            matched_route.get(

                "route_category",

                "",

            )

        ).strip()

        self._matched_category = matched_route_name

        self.status = (

            f"Routed to {matched_route_name}"

        )

        # -----------------------------------------------------

        # Deactivate all other branches

        # -----------------------------------------------------

        branches_to_stop = []

        for index, route in enumerate(routes):

            if index == matched_index:

                continue

            route_name = str(

                route.get(

                    "route_category",

                    f"Category {index + 1}",

                )

            ).strip()

            branches_to_stop.append(

                self._get_output_name(

                    index,

                    route_name,

                )

            )

        self._deactivate_branches(

            branches_to_stop

        )

        # -----------------------------------------------------

        # Return original input unless a custom route message

        # was configured.

        # -----------------------------------------------------

        custom_output = matched_route.get(

            "output_value",

            "",

        )

        if custom_output and str(

            custom_output

        ).strip():

            return Message(

                text=str(custom_output)

            )

        return Message(

            text=input_text

        )

    # ---------------------------------------------------------

    # ELSE OUTPUT

    # ---------------------------------------------------------

    def default_response(self) -> Message:

        if not getattr(

            self,

            "enable_else_output",

            False,

        ):

            return Message(text="")

        routes = getattr(

            self,

            "routes",

            [],

        ) or []

        input_text = getattr(

            self,

            "input_text",

            "",

        ) or ""

        categorization = self._get_categorization()

        # If a valid route matched, Else must not execute.

        for route in routes:

            route_name = str(

                route.get(

                    "route_category",

                    "",

                )

            ).strip()

            if (

                categorization.lower()

                == route_name.lower()

            ):

                return Message(text="")

        self.status = (

            "No Manager/Engineer match."

        )

        return Message(

            text=input_text

        )
