import importlib

modules = [
    # ── Folder Picker ──
    ".folder_picker_node",
    # ── Garment & Tag Controllers ──
    ".ak_garment_controller_node",
    ".ak_tag_controllers",
    # ── Image List Scheduler & Loaders ──
    ".ak_image_list_scheduler_node",
    ".ak_image_list_loader_node",
    ".ak_auto_image_list_loader_node",
    ".ak_reset_counters_node",
]

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for mod_name in modules:
    try:
        mod = importlib.import_module(mod_name, package=__package__)
        if hasattr(mod, "NODE_CLASS_MAPPINGS"):
            NODE_CLASS_MAPPINGS.update(mod.NODE_CLASS_MAPPINGS)
        if hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS"):
            NODE_DISPLAY_NAME_MAPPINGS.update(mod.NODE_DISPLAY_NAME_MAPPINGS)
    except Exception as e:
        print(f"[ComfyUI-AngelosKar] Error loading submodule '{mod_name}': {e}")

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
