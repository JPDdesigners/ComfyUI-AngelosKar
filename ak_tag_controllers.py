"""
AK Tag Controllers Suite
- AKTagBypasser (Generic Tag-based Bypasser)
- AKTagMuter (Generic Tag-based Muter)

Works together with AKGarmentModeController via frontend JS priority rule:
MUTE > BYPASS > ACTIVE
"""


# ─── 1. Generic Tag Bypasser ──────────────────────────────────────────────────

class AKTagBypasser:
    """
    🔀 AK Tag Bypasser (Generic)

    Switches nodes tagged with a specific keyword (e.g. [RMBG], [RESIZE], [UPSCALE])
    between ACTIVE (normal processing) and BYPASS (skip / passthrough).

    When Bypassed: the original image/data passes directly to the next node without processing.
    Priority: If a node also has [G2] and Garment 2 is off, MUTE overrides Bypass!
    """

    MODES = ["Active", "Bypass"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tag": ("STRING", {"default": "[RMBG]", "multiline": False}),
                "mode": (cls.MODES, {"default": "Active"}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_active", "tag")
    FUNCTION = "execute"
    CATEGORY = "AngelosKar/Control"
    DESCRIPTION = (
        "Generic Tag Bypasser. Switches all nodes containing the specified tag "
        "between ACTIVE and BYPASS (passthrough without processing)."
    )

    def execute(self, tag, mode):
        is_active = (mode == "Active")
        return (is_active, tag)


# ─── 2. Generic Tag Muter ─────────────────────────────────────────────────────

class AKTagMuter:
    """
    🔇 AK Tag Muter (Generic)

    Switches nodes tagged with a specific keyword (e.g. [PREVIEW], [EXTRA], [SAVE])
    between ACTIVE and MUTE (completely disabled / no execution).
    """

    MODES = ["Active", "Mute"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tag": ("STRING", {"default": "[PREVIEW]", "multiline": False}),
                "mode": (cls.MODES, {"default": "Active"}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_active", "tag")
    FUNCTION = "execute"
    CATEGORY = "AngelosKar/Control"
    DESCRIPTION = (
        "Generic Tag Muter. Switches all nodes containing the specified tag "
        "between ACTIVE and MUTE (completely disabled)."
    )

    def execute(self, tag, mode):
        is_active = (mode == "Active")
        return (is_active, tag)


# ─── Node Mappings ────────────────────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "AK_TagBypasser": AKTagBypasser,
    "AK_TagMuter": AKTagMuter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AK_TagBypasser": "🔀 AK Tag Bypasser (Active / Bypass)",
    "AK_TagMuter": "🔇 AK Tag Muter (Active / Mute)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
