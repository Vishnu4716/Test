inputs = [
    DataFrameInput(
        name="input_data",
        display_name="Input DataFrame",
        info="DataFrame from Read File.",
    ),

    MessageTextInput(
        name="query",
        display_name="Analysis Request",
        info="Manager's request for the heatmap/analysis.",
        tool_mode=True,
    ),
]
