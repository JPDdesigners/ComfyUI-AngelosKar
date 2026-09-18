import server
from aiohttp import web
import os
import sys
import threading
import ctypes
import ctypes.wintypes as wintypes
from uuid import UUID


# ─── Windows COM Helper ───────────────────────────────────────────────────────

def _guid(s):
    return (ctypes.c_byte * 16)(*UUID(s).bytes_le)


def _com_method(vtable_array, index, restype, *argtypes):
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable_array[index])


def _get_vtable(com_ptr, size=30):
    vtbl_ptr = ctypes.cast(com_ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    return ctypes.cast(vtbl_ptr, ctypes.POINTER(ctypes.c_void_p * size))[0]


# ─── Modern Explorer Dialog (IFileOpenDialog via COM) ─────────────────────────

def open_file_dialog(mode="folder", title="Select Item", file_filter=None):
    """
    Opens the modern Windows Explorer dialog.
    mode: "folder" = pick folders only | "file" = pick files
    file_filter: list of (name, pattern) tuples, e.g. [("Images", "*.jpg;*.png;*.webp")]
    """
    if sys.platform != "win32":
        return ""

    result = [None]

    def _thread():
        try:
            ole32 = ctypes.windll.ole32
            user32 = ctypes.windll.user32
            ole32.CoInitialize(None)

            # Create IFileOpenDialog
            pDlg = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                ctypes.byref(_guid('{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}')),
                None, 1,
                ctypes.byref(_guid('{D57C7288-D4AD-4768-BE02-9D969532D960}')),
                ctypes.byref(pDlg)
            )
            if hr != 0:
                ole32.CoUninitialize()
                return

            vt = _get_vtable(pDlg)
            Release    = _com_method(vt, 2,  ctypes.c_ulong)
            Show       = _com_method(vt, 3,  ctypes.HRESULT, wintypes.HWND)
            SetOptions = _com_method(vt, 9,  ctypes.HRESULT, ctypes.c_uint)
            GetOptions = _com_method(vt, 10, ctypes.HRESULT, ctypes.POINTER(ctypes.c_uint))
            SetTitle   = _com_method(vt, 17, ctypes.HRESULT, ctypes.c_wchar_p)
            GetResult  = _com_method(vt, 20, ctypes.HRESULT, ctypes.POINTER(ctypes.c_void_p))

            # File type filter for file mode
            if mode == "file" and file_filter:
                class COMDLG_FILTERSPEC(ctypes.Structure):
                    _fields_ = [("pszName", ctypes.c_wchar_p), ("pszSpec", ctypes.c_wchar_p)]

                SetFileTypes = _com_method(vt, 4, ctypes.HRESULT, ctypes.c_uint,
                                           ctypes.POINTER(COMDLG_FILTERSPEC))
                filters = (COMDLG_FILTERSPEC * len(file_filter))(
                    *[COMDLG_FILTERSPEC(n, s) for n, s in file_filter]
                )
                SetFileTypes(pDlg, len(file_filter), filters)

            # Options — minimal flags so Windows shows ALL files inside folders
            opts = ctypes.c_uint()
            GetOptions(pDlg, ctypes.byref(opts))
            if mode == "folder":
                # FOS_PICKFOLDERS only — no extra flags that might hide files
                SetOptions(pDlg, 0x20 | 0x800)  # PICKFOLDERS + PATHMUSTEXIST
            else:
                flags = opts.value | 0x40  # FOS_FORCEFILESYSTEM
                SetOptions(pDlg, flags)
            SetTitle(pDlg, title)

            # ── Topmost trick: invisible owner window ──
            hwnd_owner = user32.CreateWindowExW(
                0x00000008 | 0x00000080,   # WS_EX_TOPMOST | WS_EX_TOOLWINDOW
                "Static", "", 0,
                0, 0, 0, 0,
                None, None, None, None
            )
            user32.SetForegroundWindow(hwnd_owner)

            hr = Show(pDlg, hwnd_owner)
            user32.DestroyWindow(hwnd_owner)

            if hr == 0:
                pItem = ctypes.c_void_p()
                if GetResult(pDlg, ctypes.byref(pItem)) == 0 and pItem:
                    ivt = _get_vtable(pItem, 10)
                    GetDisplayName = _com_method(ivt, 5, ctypes.HRESULT,
                                                 ctypes.c_uint, ctypes.POINTER(ctypes.c_wchar_p))
                    path_ptr = ctypes.c_wchar_p()
                    if GetDisplayName(pItem, 0x80058000, ctypes.byref(path_ptr)) == 0:
                        if path_ptr.value:
                            result[0] = path_ptr.value
                        ole32.CoTaskMemFree(ctypes.cast(path_ptr, ctypes.c_void_p))
                    _com_method(ivt, 2, ctypes.c_ulong)(pItem)  # Release

            Release(pDlg)
            ole32.CoUninitialize()
        except Exception as e:
            print(f"[AngelosKar] Dialog error: {e}")

    t = threading.Thread(target=_thread)
    t.daemon = True
    t.start()
    t.join(timeout=120)
    return result[0] or ""


# ─── API Routes ───────────────────────────────────────────────────────────────

try:
    if hasattr(server, "PromptServer") and hasattr(server.PromptServer, "instance") and server.PromptServer.instance is not None:
        @server.PromptServer.instance.routes.post("/angeloskar/choose_folder")
        async def choose_folder(request):
            path = open_file_dialog(mode="folder", title="Select Image Directory")
            return web.json_response({"path": path})

        @server.PromptServer.instance.routes.post("/angeloskar/choose_image")
        async def choose_image(request):
            path = open_file_dialog(
                mode="file",
                title="Select Image File",
                file_filter=[
                                        (
                        "Images",
                        "*.jpg;*.jpeg;*.png;"
                        "*.webp;*.bmp;*.tiff;*.gif",
                    ),
                    ("All Files", "*.*"),
                ]
            )
            return web.json_response({"path": path})
except Exception as e:
    print(f"[AngelosKar] Warning: Failed to register server routes: {e}")


# ─── ComfyUI Node ─────────────────────────────────────────────────────────────

class FolderPickerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:\\", "multiline": False})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("folder_path",)
    FUNCTION = "get_path"
    CATEGORY = "AngelosKar/Utils"
    DESCRIPTION = "Opens the modern Windows Explorer dialog to select an image directory."

    def get_path(self, folder_path):
        return (folder_path,)


NODE_CLASS_MAPPINGS = {
    "AK_FolderPicker": FolderPickerNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AK_FolderPicker": "📂 AK Folder Path Picker"
}
