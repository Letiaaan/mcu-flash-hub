"""Read process liveness without inspecting or terminating unrelated processes."""
import os
import sys


def is_running(pid):
    if not pid:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        process = kernel.OpenProcess(0x1000, False, pid)
        if not process:
            return ctypes.get_last_error() == 5  # Do not call an inaccessible process stopped.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(process, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(process)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
