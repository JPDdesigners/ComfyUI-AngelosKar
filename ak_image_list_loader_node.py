import os
import re
import time
import fnmatch
import numpy as np
import torch
from PIL import Image, ImageOps


class ImageListLoaderNode:
    """
    📦 Image List Loader (AK)

    Loads a slice of images from one folder and outputs them as lists,
    so downstream nodes can process each image one-by-one through ComfyUI list mapping.

    Designed for batch/list workflows driven by a scheduler.
    Reads only the exact input folder. No subfolder scanning.
    """

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif'}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"forceInput": True}),
                "sorting": ("STRING", {"forceInput": True}),
                "file_pattern": ("STRING", {"forceInput": True}),
                "start_index": ("INT", {"forceInput": True}),
                "list_size": ("INT", {"forceInput": True}),
                "file_name_without_extension": ("BOOLEAN", {"default": True, "label_on": "Yes", "label_off": "No"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "filenames")
    FUNCTION = "load_list"
    CATEGORY = "AngelosKar/Batch"
    DESCRIPTION = "Loads a slice of images from a folder and outputs them as lists, so downstream nodes can process each image one-by-one."

    # Important:
    # IMAGE and filenames are lists.
    # This makes ComfyUI pass each image/name item one-by-one to the next mapped node,
    # instead of creating one big tensor batch in memory.
    OUTPUT_IS_LIST = (True, True)

    @staticmethod
    def _natural_sort_key(name):
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', name)
        ]

    def _get_image_files(self, folder_path, file_pattern, sorting):
        if not os.path.isdir(folder_path):
            raise ValueError(f"[AngelosKar] Folder not found: {folder_path}")

        pattern = (file_pattern or "*").strip()
        if not pattern:
            pattern = "*"

        pattern_lower = pattern.lower()

        try:
            files = []
            for fname in os.listdir(folder_path):
                fpath = os.path.join(folder_path, fname)

                # Flat folder only. Do not scan subfolders.
                if not os.path.isfile(fpath):
                    continue

                if os.path.splitext(fname)[1].lower() not in self.EXTENSIONS:
                    continue

                # Case-insensitive filename pattern matching, like OreX.
                if not fnmatch.fnmatch(fname.lower(), pattern_lower):
                    continue

                files.append(fname)
        except Exception as e:
            raise ValueError(f"[AngelosKar] Failed to read folder: {folder_path} | {e}")

        if sorting == "natural":
            files.sort(key=self._natural_sort_key)
        else:
            files.sort(key=lambda s: s.lower())

        return files

    def load_list(
        self,
        folder_path,
        sorting="natural",
        file_pattern="*",
        start_index=0,
        list_size=1,
        file_name_without_extension=True,
    ):
        files = self._get_image_files(folder_path, file_pattern, sorting)
        total_files = len(files)

        if total_files == 0:
            raise ValueError(
                f"[AngelosKar] No images found in: {folder_path} (pattern: {file_pattern})"
            )

        if start_index < 0:
            start_index = 0

        selected_files = files[start_index:start_index + list_size]

        if not selected_files:
            raise ValueError(
                f"[AngelosKar] No images at index {start_index} "
                f"(total: {total_files}, requested: {list_size})"
            )

        images = []
        filenames = []

        for fname in selected_files:
            fpath = os.path.join(folder_path, fname)

            try:
                img = ImageOps.exif_transpose(Image.open(fpath)).convert("RGB")
                img_array = np.array(img).astype(np.float32) / 255.0
                img_tensor = torch.from_numpy(img_array).unsqueeze(0)

                images.append(img_tensor)
                filenames.append(os.path.splitext(fname)[0] if file_name_without_extension else fname)

            except Exception as e:
                print(f"[AngelosKar] Failed to load {fname}: {e}")

        if not images:
            raise ValueError("[AngelosKar] Failed to load any images from selected list.")

        print(
            f"[AngelosKar] 📦 Loaded {len(images)} image list items "
            f"from index {start_index} / total {total_files}"
        )

        return (images, filenames)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()


NODE_CLASS_MAPPINGS = {
    "AK_ImageListLoader": ImageListLoaderNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AK_ImageListLoader": "📦 AK Image List Loader (Scheduler)"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
