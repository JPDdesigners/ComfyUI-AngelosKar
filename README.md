# ComfyUI-AngelosKar

A clean, modular custom node pack for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) focused on automated batch image processing, modern folder selection, multi-garment VTON workflow control, and dynamic canvas tag toggling.

---

## 🌟 Features

* **Sequential Image Scheduling**: Process entire folders chunk-by-chunk using native ComfyUI *Run on Change* without moving or modifying files.
* **VRAM-Safe List Execution**: Outputs images as Python lists rather than heavy 4D tensors, enabling ComfyUI list mapping to process images individually.
* **Canvas Tag Controllers**: Dynamically Bypass or Mute canvas nodes simply by adding tags (e.g., `[RMBG]`, `[PREVIEW]`) to their titles.
* **Multi-Garment VTON Mode Control**: Switch between 1 to 5 garments dynamically with automatic canvas muting for `[G2]`, `[G3]`, `[G4]`, `[G5]`.
* **Native Windows Folder Dialog**: Open modern Windows Explorer folder picker directly from the node.
* **One-Click Counter Resets**: Interactive frontend buttons to instantly reset batch progress without restarting ComfyUI.

---

## 📦 Nodes & Categories

### 1. `AngelosKar/Batch`

* **📊 AK Image List Scheduler (`AK_ImageListScheduler`)**
  * Schedules slice-by-slice image runs across queue executions.
  * Inputs: `folder_path`, `list_size`, `file_pattern`, `sorting` (*natural* or *alphabetical*), `load_remainder` (*on/off*), `remainder_position` (*start/end*).
  * Has an interactive **📂 Browse Folder** button and **🔄 Reset Counter** button.
  * Outputs: `folder_path`, `sorting`, `file_pattern`, `start_index`, `list_size`, `total_images`, `run_counter`, `total_runs`, `folder_analysis`.
  * Designed to be connected directly to **📦 AK Image List Loader**.

* **📦 AK Image List Loader (Scheduler) (`AK_ImageListLoader`)**
  * Worker node that receives inputs from the Scheduler and loads the scheduled slice of images.
  * Outputs images as an **IMAGE list** (`OUTPUT_IS_LIST = True`), allowing downstream nodes to execute one-by-one with full resolution preservation.

* **🔄 AK Auto Image List Loader (`AK_AutoImageListLoader`)**
  * All-in-one standalone node combining both the Scheduler and Loader into a single node.
  * Ideal for simple, compact batch workflows.

* **🔄 AK Reset Counters (`AK_ResetCounters`)**
  * Utility canvas button. Place it anywhere on the canvas and click **🔄 Reset All Counters** to reset all scheduler counters in the active workflow back to 0.

---

### 2. `AngelosKar/Control`

* **🔀 AK Tag Bypasser (Active / Bypass) (`AK_TagBypasser`)**
  * Switches all canvas nodes matching a specified tag (e.g. `[RMBG]`, `[UPSCALE]`, `[FACE]`) between **ACTIVE** and **BYPASS** (passthrough).

* **🔇 AK Tag Muter (Active / Mute) (`AK_TagMuter`)**
  * Switches all canvas nodes matching a specified tag (e.g. `[PREVIEW]`, `[SAVE]`, `[EXTRA]`) between **ACTIVE** and **MUTE** (disabled / skipped).

> **Canvas Priority Rule**: If multiple controllers target the same node, the strict hierarchy is **MUTE > BYPASS > ACTIVE**.

---

### 3. `AngelosKar/VTON`

* **👔 AK Garment Mode Controller (1-5) (`AK_GarmentModeController`)**
  * Designed for multi-garment Virtual Try-On (VTON) workflows.
  * Select active garments from **1 Garment** up to **5 Garments**.
  * Automatically mutes nodes tagged with `[G2]`, `[G3]`, `[G4]`, or `[G5]` when that garment number is disabled. Nodes without garment tags are left untouched.

---

### 4. `AngelosKar/Utils`

* **📂 AK Folder Path Picker (`AK_FolderPicker`)**
  * Interactive node with a **📂 Browse Folder** button that opens the native Windows Explorer folder selection dialog and outputs the selected folder path string.

---

## 🚀 Installation

### Option 1: ComfyUI-Manager (Recommended)
1. In ComfyUI, open **ComfyUI-Manager**.
2. Search for `ComfyUI-AngelosKar`.
3. Click **Install** and restart ComfyUI.

### Option 2: Comfy-CLI
```bash
comfy node install comfyui-angeloskar
```

### Option 3: Manual Git Clone
1. Open a terminal in your `ComfyUI/custom_nodes/` directory.
2. Clone the repository:
   ```bash
   git clone https://github.com/AngelosKar-code/ComfyUI-AngelosKar.git
   ```
3. Restart ComfyUI.

---

## 🛠 Requirements

* Python >= 3.10
* ComfyUI (frontend v1.x or v2.x)
* Dependencies:
  * `torch`
  * `numpy`
  * `Pillow`
  * `aiohttp`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
