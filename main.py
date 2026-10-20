"""Early CLI dispatch is required for packaged backend subprocesses."""
import sys


def main():
    # A windowed PyInstaller app has no stdout; attach a pipe for the child CLI.
    if len(sys.argv) > 1 and sys.argv[1] in ("--tool", "--simulate", "--self-test"):
        if sys.stdout is None or sys.stderr is None:
            import os
            import ctypes
            import msvcrt
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetStdHandle.argtypes = [ctypes.c_ulong]
            kernel.GetStdHandle.restype = ctypes.c_void_p
            for name, number in (("stdout", -11), ("stderr", -12)):
                if getattr(sys, name) is None:
                    handle = kernel.GetStdHandle(number & 0xFFFFFFFF)
                    if handle and handle != ctypes.c_void_p(-1).value:
                        descriptor = msvcrt.open_osfhandle(handle, os.O_WRONLY)
                        setattr(sys, name, os.fdopen(descriptor, "w", encoding="utf-8", buffering=1, closefd=False))
                    else:
                        setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        if sys.argv[1] == "--self-test":
            from flashdesk.selftest import run
            return run(sys.argv[2])
        if sys.argv[1] == "--simulate":
            from flashdesk.simulator import run
            return run(sys.argv[2])
        tool = sys.argv[2]
        sys.argv = [tool] + sys.argv[3:]
        if tool == "esptool":
            import esptool
            esptool._main()
            return 0
        if tool == "stcgal":
            from stcgal.frontend import cli
            return cli()
        raise ValueError("Unknown bundled tool")
    from flashdesk.app import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
