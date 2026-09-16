import os
import re
import time
import fnmatch
import numpy as np
import torch
from PIL import Image, ImageOps
import server
from aiohttp import web


# ─── API: Reset counter ──────────────────────────────────────────────────────

try:
    if hasattr(server, "PromptServer") and hasattr(server.PromptServer, "instance") and server.PromptServer.instance is not None:
        @server.PromptServer.instance.routes.post("/angeloskar/reset_auto_list_counter")
        async def reset_auto_list_counter(request):
            data = await request.json()
            uid = str(data.get("unique_id", ""))

            if uid in AutoImageListLoaderNode._counters:
                AutoImageListLoaderNode._counters[uid] = 0
                AutoImageListLoaderNode._settings_hashes.pop(uid, None)
                print(f"[AngelosKar] 🔄 Auto list counter reset for node {uid}")
                return web.json_response({"status": "ok", "message": "Counter reset to 0"})

            return web.json_response({"status": "ok", "message": "No active counter (already at 0)"})
except Exception as e:
    print(f"[AngelosKar] Warning: Failed to register reset_auto_list_counter route: {e}")


class AutoImageListLoaderNode:
    """
    🔄 Auto Image List Loader (AK)

    All-in-one node: scans a folder, schedules runs, and loads images
    automatically. Combines the functionality of Image List Scheduler
    and Image List Loader into a single node.

    Usage:
    - Set folder, list_size, and other options.
    - Enable ComfyUI "Run on Change" or queue multiple times.
    - Each run loads the next chunk of images automatically.
    - When all images are processed, raises a controlled error to stop.

    For advanced/modular workflows, use the separate
    📊 Image List Scheduler + 📦 Image List Loader pair instead.
    """

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif'}

    # Class-level state — persists across queue runs
    _counters = {}
    _settings_hashes = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:\\", "multiline": False}),
                "list_size": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
                "file_pattern": ("STRING", {"default": "*", "multiline": False}),
                "sorting": (["natural", "alphabetical"], {"default": "natural"}),
                "load_remainder": (["on", "off"], {"default": "on"}),
                "remainder_position": (["end", "start"], {"default": "end"}),
                "file_name_without_extension": ("BOOLEAN", {"default": True,
                                                            "label_on": "Yes",
                                                            "label_off": "No"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT", "INT", "STRING")
    RETURN_NAMES = (
        "images",
        "filenames",
        "total_images",
        "run_counter",
        "total_runs",
        "folder_analysis",
    )
    OUTPUT_IS_LIST = (True, True, False, False, False, False)
    FUNCTION = "execute"
    CATEGORY = "AngelosKar/Batch"
    DESCRIPTION = "All-in-one node: scans a folder, schedules runs, and loads images automatically. Combines the functionality of Image List Scheduler and Image List Loader into a single node."

    # ── File scanning ─────────────────────────────────────────────────────

    @staticmethod
    def _natural_sort_key(filename):
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', filename)
        ]

    def _get_image_files(self, folder_path, file_pattern, sorting):
        """Flat-folder only. Case-insensitive pattern. No subfolder scanning."""
        if not os.path.isdir(folder_path):
            return []

        pattern = (file_pattern or "*").strip() or "*"
        pattern_lower = pattern.lower()

        try:
            files = [
                fname for fname in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, fname))
                and os.path.splitext(fname)[1].lower() in self.EXTENSIONS
                and fnmatch.fnmatch(fname.lower(), pattern_lower)
            ]
        except Exception as e:
            raise ValueError(f"[AngelosKar] Could not read folder: {folder_path} ({e})")

        if sorting == "natural":
            files.sort(key=self._natural_sort_key)
        else:
            files.sort(key=lambda s: s.lower())

        return files

    # ── Run calculation ───────────────────────────────────────────────────

    @staticmethod
    def _get_total_runs(total, list_size, load_remainder):
        if total <= 0:
            return 0
        full_runs = total // list_size
        remainder = total % list_size
        if full_runs == 0:
            return 1 if load_remainder == "on" else 0
        if remainder > 0 and load_remainder == "on":
            return full_runs + 1
        return full_runs

    @staticmethod
    def _calculate_run(counter, total, list_size, load_remainder, remainder_position):
        """Return (start_index, count), or None when all runs are completed."""
        if total <= 0:
            return None
        full_runs = total // list_size
        remainder = total % list_size
        has_remainder = remainder > 0

        if full_runs == 0:
            if load_remainder == "on" and counter == 0:
                return 0, total
            return None

        total_runs = full_runs + 1 if load_remainder == "on" and has_remainder else full_runs
        if counter >= total_runs:
            return None

        if load_remainder == "on" and has_remainder:
            if remainder_position == "start":
                if counter == 0:
                    return 0, remainder
                start = remainder + (counter - 1) * list_size
                return start, list_size
            # end
            if counter < full_runs:
                return counter * list_size, list_size
            return full_runs * list_size, remainder

        return counter * list_size, list_size

    # ── Settings hash ─────────────────────────────────────────────────────

    def _build_settings_hash(self, folder_path, list_size, file_pattern, sorting,
                             load_remainder, remainder_position, files):
        if files:
            file_signature = f"{len(files)}|{files[0]}|{files[-1]}"
        else:
            file_signature = "0||"
        return "|".join([
            folder_path, str(list_size), file_pattern, sorting,
            load_remainder, remainder_position, file_signature,
        ])

    # ── Info text ─────────────────────────────────────────────────────────

    def _build_info_text(self, files, file_pattern, list_size,
                         load_remainder, remainder_position,
                         counter, run_result, total_runs):
        total = len(files)
        pattern = (file_pattern or "*").strip() or "*"

        if total == 0:
            return "No images found in folder."

        full_runs = total // list_size
        remainder = total % list_size
        has_remainder = remainder > 0

        lines = [
            "=== Auto Image List Loader Analysis ===",
            f"Total images found: {total}",
            f"File pattern: {pattern}",
        ]

        if pattern == "*":
            lines.append(f"All {total} images match the pattern.")
        else:
            lines.append(f"{total} images match '{pattern}' case-insensitively.")

        lines += ["", f"List size per run: {list_size}", f"Full runs: {full_runs}"]

        if has_remainder:
            lines.append(f"Remainder: {remainder} images")
            lines.append(f"Load remainder: {load_remainder.upper()}")
            if load_remainder == "on":
                lines.append(f"Remainder position: {remainder_position.upper()}")
                if remainder_position == "start":
                    lines.append(f"  -> first run loads {remainder}, then {full_runs}x{list_size}")
                else:
                    lines.append(f"  -> {full_runs}x{list_size}, then last run loads {remainder}")
            else:
                lines.append(f"  -> {full_runs}x{list_size} = {full_runs * list_size} images processed")
                lines.append(f"  -> {remainder} images skipped")
        else:
            lines.append(f"Perfect split: {full_runs}x{list_size}")

        lines += ["", f"Total scheduled runs: {total_runs}",
                   "Run on Change mode: final controlled error stops the loop."]

        if run_result is not None:
            start, count = run_result
            lines += ["", f"--- Current run {counter + 1}/{total_runs} ---",
                       f"Loading {count} image(s) from index {start}"]
            preview = files[start:start + min(count, 5)]
            for i, fname in enumerate(preview):
                lines.append(f"  {i + 1}. {fname}")
            if count > 5:
                lines.append(f"  ... +{count - 5} more")
        else:
            lines += ["", f"✅ ALL {total_runs} RUNS COMPLETED!",
                       "Reset counter to run again."]

        return "\n".join(lines)

    # ── Main execution ────────────────────────────────────────────────────

    def execute(self, folder_path, list_size=10, file_pattern="*",
                sorting="natural", load_remainder="on",
                remainder_position="end", file_name_without_extension=True,
                unique_id=None):

        uid = str(unique_id) if unique_id else "_default"
        files = self._get_image_files(folder_path, file_pattern, sorting)
        total = len(files)

        # ── Counter management ──
        settings_hash = self._build_settings_hash(
            folder_path, list_size, file_pattern, sorting,
            load_remainder, remainder_position, files,
        )
        if uid not in self._settings_hashes or self._settings_hashes[uid] != settings_hash:
            self._counters[uid] = 0
            self._settings_hashes[uid] = settings_hash
            print("[AngelosKar] 🔄 Auto list counter auto-reset")

        counter = self._counters.get(uid, 0)
        total_runs = self._get_total_runs(total, list_size, load_remainder)

        # ── No images ──
        if total == 0:
            analysis = self._build_info_text(
                files, file_pattern, list_size, load_remainder,
                remainder_position, counter, None, 0,
            )
            raise ValueError(
                f"[AngelosKar] No images found in: {folder_path} "
                f"(pattern: {file_pattern})\n\n{analysis}"
            )

        # ── Calculate current run ──
        run_result = self._calculate_run(
            counter, total, list_size, load_remainder, remainder_position,
        )
        analysis = self._build_info_text(
            files, file_pattern, list_size, load_remainder,
            remainder_position, counter, run_result, total_runs,
        )

        if run_result is None:
            print(f"[AngelosKar] ✅ All {total_runs} auto list runs completed")
            raise ValueError(
                f"[AngelosKar] ✅ All {total_runs} runs completed. "
                f"No more images. Reset counter to run again."
            )

        start_index, count = run_result
        run_counter = counter + 1

        # ── Load images ──
        selected_files = files[start_index:start_index + count]
        images = []
        filenames = []

        for fname in selected_files:
            fpath = os.path.join(folder_path, fname)
            try:
                img = ImageOps.exif_transpose(Image.open(fpath)).convert("RGB")
                img_array = np.array(img).astype(np.float32) / 255.0
                img_tensor = torch.from_numpy(img_array).unsqueeze(0)
                images.append(img_tensor)
                filenames.append(
                    os.path.splitext(fname)[0] if file_name_without_extension else fname
                )
            except Exception as e:
                print(f"[AngelosKar] Failed to load {fname}: {e}")

        if not images:
            raise ValueError("[AngelosKar] Failed to load any images from current run.")

        # Increment counter only after successful load
        self._counters[uid] = counter + 1

        print(
            f"[AngelosKar] 🔄 Auto list run {run_counter}/{total_runs}: "
            f"loaded {len(images)} images from index {start_index}"
        )

        return (images, filenames, total, run_counter, total_runs, analysis)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()


NODE_CLASS_MAPPINGS = {
    "AK_AutoImageListLoader": AutoImageListLoaderNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AK_AutoImageListLoader": "🔄 AK Auto Image List Loader",
}
