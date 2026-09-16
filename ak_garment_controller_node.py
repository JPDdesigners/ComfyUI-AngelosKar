"""
AK Garment Mode Controller
Provides automatic Mute / Un-mute control for multi-garment VTON workflows (up to 5 garments).
Controls nodes dynamically across the canvas using tags: [G2], [G3], [G4], [G5].
"""

class AKGarmentModeController:
    """
    👔 AK Garment Mode Controller (1-5 Garments)

    Controls which garment paths are active or muted across your workflow.
    Works automatically via frontend JavaScript tags in node titles:
      • [G2] in node title -> Active when 2, 3, 4, or 5 garments selected (Muted when 1)
      • [G3] in node title -> Active when 3, 4, or 5 garments selected (Muted when 1 or 2)
      • [G4] in node title -> Active when 4 or 5 garments selected (Muted when 1, 2, or 3)
      • [G5] in node title -> Active when 5 garments selected (Muted when 1, 2, 3, or 4)

    Nodes without tags (like Garment 1, Gemini, Save Image) are never touched.
    """

    MODES = [
        "1 Garment",
        "2 Garments",
        "3 Garments",
        "4 Garments",
        "5 Garments",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "active_garments": (cls.MODES, {"default": "1 Garment"}),
            },
            "optional": {
                "auto_mute_on_queue": ("BOOLEAN", {
                    "default": True,
                    "label_on": "Yes (Auto Mute)",
                    "label_off": "No (Manual Only)"
                }),
            },
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("garment_count", "active_mode")
    FUNCTION = "get_mode"
    CATEGORY = "AngelosKar/VTON"
    DESCRIPTION = (
        "Controls multi-garment workflows (1-5). "
        "Automatically mutes/unmutes nodes tagged with [G2], [G3], [G4], [G5] anywhere in the canvas."
    )

    def get_mode(self, active_garments, auto_mute_on_queue=True):
        try:
            count = int(active_garments.split()[0])
        except Exception:
            count = 1
        return (count, active_garments)


NODE_CLASS_MAPPINGS = {
    "AK_GarmentModeController": AKGarmentModeController
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AK_GarmentModeController": "👔 AK Garment Mode Controller (1-5)"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
