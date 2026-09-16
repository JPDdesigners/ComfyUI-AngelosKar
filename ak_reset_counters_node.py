class ResetCountersNode:
    """
    🔄 Reset Counters (AK)

    Utility node — place it anywhere on your canvas.
    Click the button to reset ALL Image List Scheduler and
    Auto Image List Loader counters in the current workflow.

    No wiring needed. The reset button works via the JS frontend,
    automatically finding all AK scheduler nodes in the graph.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ()
    FUNCTION = "noop"
    CATEGORY = "AngelosKar/Batch"
    DESCRIPTION = "Click the button to reset ALL Image List Scheduler and Auto Image List Loader counters in the current workflow."
    OUTPUT_NODE = True

    def noop(self):
        # This node never needs to execute.
        # The reset button is handled entirely by the JS frontend.
        return ()

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return ""


NODE_CLASS_MAPPINGS = {
    "AK_ResetCounters": ResetCountersNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AK_ResetCounters": "🔄 AK Reset Counters",
}
