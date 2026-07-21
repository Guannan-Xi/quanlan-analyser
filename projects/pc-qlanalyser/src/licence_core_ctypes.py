"""
Python ctypes wrapper for the NeuroRecorder licence_core dynamic library.

This module focuses on the Windows build of the library, but it will also
work on other platforms provided a compatible shared library is available.
"""

from __future__ import annotations

import ctypes
import os
import pathlib
from enum import IntEnum
from typing import Optional


class LicenceError(RuntimeError):
    """Raised when the licence core library reports an error."""


class LicenceResult(IntEnum):
    INIT = -1
    NORMAL = 0
    NO_AUTH_FILE = 1
    ILLEGAL = 2
    FILE_ABNORMAL = 3
    NOT_LOCAL_AUTH_FILE = 4
    NOT_AVAILABLE = 5
    AUTH_TIME_ABNORMAL = 6
    USE_TIME_ABNORMAL = 7
    TRIAL_EXPIRED = 8
    AUTH_EXPIRED = 9


def _default_search_paths() -> list[pathlib.Path]:
    base_dir = pathlib.Path(__file__).resolve().parent.parent
    candidates = [
        base_dir / "out" / "build" / "x64-Debug",
        base_dir / "out" / "build" / "x64-Release",
        base_dir / "build" / "licence_core",
        base_dir,
    ]
    env_path = os.getenv("LICENCE_CORE_DLL_PATH")
    if env_path:
        candidates.insert(0, pathlib.Path(env_path))
    return candidates


def _library_name() -> str:
    if os.name == "nt":
        return "licence_core.dll"
    if os.name == "posix":
        return "liblicence_core.so"
    return "licence_core.dll"


def _load_library(explicit_path: Optional[os.PathLike[str] | str] = None) -> ctypes.CDLL:
    if explicit_path:
        search = [pathlib.Path(explicit_path)]
    else:
        search = _default_search_paths()

    lib_name = _library_name()
    last_error: Optional[Exception] = None
    for directory in search:
        candidate = directory if directory.suffix else directory / lib_name
        if candidate.is_dir():
            candidate = candidate / lib_name
        if not candidate.exists():
            continue
        try:
            if os.name == "nt":
                # Ensure dependent DLLs can be located.
                os.add_dll_directory(str(candidate.parent))
                return ctypes.WinDLL(str(candidate))
            return ctypes.CDLL(str(candidate))
        except OSError as exc:
            last_error = exc
            continue

    raise LicenceError(
        f"Unable to load {lib_name}. "
        f"Checked: {', '.join(str(p) for p in search)}"
        + (f" (last error: {last_error})" if last_error else "")
    )


class _Library:
    """Internal helper that loads and prepares ctypes signatures."""

    def __init__(self, path: Optional[os.PathLike[str] | str] = None) -> None:
        self._dll = _load_library(path)
        self._configure()

    def _configure(self) -> None:
        c_void_p = ctypes.c_void_p
        c_char_p = ctypes.c_char_p
        c_int = ctypes.c_int
        c_double = ctypes.c_double

        self._dll.licence_core_create.restype = c_void_p
        self._dll.licence_core_create.argtypes = [c_char_p]

        self._dll.licence_core_destroy.restype = None
        self._dll.licence_core_destroy.argtypes = [c_void_p]

        self._dll.licence_core_check.restype = c_int
        self._dll.licence_core_check.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p, c_int]

        self._dll.licence_core_get_last_error.restype = c_char_p
        self._dll.licence_core_get_last_error.argtypes = [c_void_p]

        self._dll.licence_core_update_last_use.restype = None
        self._dll.licence_core_update_last_use.argtypes = [c_void_p, c_char_p]

        # Info getters
        self._dll.licence_core_get_trial_days.restype = c_int
        self._dll.licence_core_get_trial_days.argtypes = [c_void_p]

        self._dll.licence_core_get_valid_days.restype = c_int
        self._dll.licence_core_get_valid_days.argtypes = [c_void_p]

        self._dll.licence_core_get_board_mac.restype = c_char_p
        self._dll.licence_core_get_board_mac.argtypes = [c_void_p]

        self._dll.licence_core_get_auth_time.restype = c_char_p
        self._dll.licence_core_get_auth_time.argtypes = [c_void_p]

        self._dll.licence_core_get_last_use_time.restype = c_char_p
        self._dll.licence_core_get_last_use_time.argtypes = [c_void_p]

        for name in (
            "stim",
            "edit",
            "micro_state",
            "simu",
            "filter",
        ):
            func = getattr(self._dll, f"licence_core_is_{name}_enabled")
            func.restype = c_int
            func.argtypes = [c_void_p]

        # Evaluation getters
        self._dll.licence_core_get_result_code.restype = c_int
        self._dll.licence_core_get_result_code.argtypes = [c_void_p]

        self._dll.licence_core_get_used_days.restype = c_double
        self._dll.licence_core_get_used_days.argtypes = [c_void_p]

        self._dll.licence_core_get_remaining_days.restype = c_double
        self._dll.licence_core_get_remaining_days.argtypes = [c_void_p]

        # Machine code helpers
        self._dll.licence_core_get_baseboard_serial.restype = c_char_p
        self._dll.licence_core_get_baseboard_serial.argtypes = []

        self._dll.licence_core_get_baseboard_serial_raw.restype = c_char_p
        self._dll.licence_core_get_baseboard_serial_raw.argtypes = []

    @property
    def dll(self) -> ctypes.CDLL:
        return self._dll


_LIBRARY_INSTANCE: Optional[_Library] = None


def _lib(path: Optional[os.PathLike[str] | str] = None) -> _Library:
    global _LIBRARY_INSTANCE
    if _LIBRARY_INSTANCE is None or path:
        _LIBRARY_INSTANCE = _Library(path)
    return _LIBRARY_INSTANCE


def get_machine_code(path: Optional[os.PathLike[str] | str] = None) -> Optional[str]:
    """Return the formatted machine code (MD5 with hyphen groups)."""
    lib = _lib(path).dll
    result = lib.licence_core_get_baseboard_serial()
    return result.decode("utf-8") if result else None


def get_raw_serial(path: Optional[os.PathLike[str] | str] = None) -> Optional[str]:
    """Return the raw motherboard serial string."""
    lib = _lib(path).dll
    result = lib.licence_core_get_baseboard_serial_raw()
    return result.decode("utf-8") if result else None

def l_d_path(name: str, ensure_dir: bool = False) -> pathlib.Path | None:
    """返回资源图片的完整路径。
    - ensure_dir=False（默认）：只读模式，文件不存在则返回 None。
    - ensure_dir=True：写入模式，需要时创建父目录并返回路径（即使文件现在不存在）。
    """
    here = pathlib.Path(__file__).resolve().parent
    p = here.parent / "resource" / name
    if ensure_dir:
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return p if p.exists() else None
class LicenceCore:
    """High-level wrapper around the licence core handle."""

    def __init__(self, hardware_serial: str, dll_path: Optional[os.PathLike[str] | str] = None) -> None:
        if not hardware_serial:
            raise ValueError("hardware_serial must be a non-empty string")
        dll_path = l_d_path("licence_core.dll")
        self._library = _lib(dll_path)
        self._dll = self._library.dll
        self._handle = self._dll.licence_core_create(hardware_serial.encode("utf-8"))
        if not self._handle:
            raise LicenceError("Failed to create licence core handle")

    def __enter__(self) -> "LicenceCore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._handle:
            self._dll.licence_core_destroy(self._handle)
            self._handle = None

    def check(
        self,
        licence_text: str,
        last_use_time: str | None = None,
        current_time_iso: str | None = None,
        check_clock_drift: bool = True,
    ) -> LicenceResult:
        if not self._handle:
            raise LicenceError("Licence handle is not valid")
        licence_bytes = licence_text.encode("utf-8")
        last_use_bytes = (last_use_time or "").encode("utf-8")
        current_time_bytes = current_time_iso.encode("utf-8") if current_time_iso else None
        result = self._dll.licence_core_check(
            self._handle,
            licence_bytes,
            last_use_bytes,
            current_time_bytes,
            1 if check_clock_drift else 0,
        )
        return LicenceResult(result)

    def update_last_use(self, current_time_iso: Optional[str] = None) -> None:
        if not self._handle:
            raise LicenceError("Licence handle is not valid")
        current_time_bytes = current_time_iso.encode("utf-8") if current_time_iso else None
        self._dll.licence_core_update_last_use(self._handle, current_time_bytes)

    def last_error(self) -> str:
        if not self._handle:
            return ""
        err = self._dll.licence_core_get_last_error(self._handle)
        return err.decode("utf-8") if err else ""

    # Convenience accessors -------------------------------------------------

    def trial_days(self) -> int:
        return int(self._dll.licence_core_get_trial_days(self._handle))

    def valid_days(self) -> int:
        return int(self._dll.licence_core_get_valid_days(self._handle))

    def board_mac(self) -> Optional[str]:
        result = self._dll.licence_core_get_board_mac(self._handle)
        return result.decode("utf-8") if result else None

    def auth_time(self) -> Optional[str]:
        result = self._dll.licence_core_get_auth_time(self._handle)
        return result.decode("utf-8") if result else None

    def last_use_time(self) -> Optional[str]:
        result = self._dll.licence_core_get_last_use_time(self._handle)
        return result.decode("utf-8") if result else None

    def feature_flags(self) -> dict[str, bool]:
        dll = self._dll
        handle = self._handle
        return {
            "stim_enabled": bool(dll.licence_core_is_stim_enabled(handle)),
            "edit_enabled": bool(dll.licence_core_is_edit_enabled(handle)),
            "micro_state_enabled": bool(dll.licence_core_is_micro_state_enabled(handle)),
            "simu_enabled": bool(dll.licence_core_is_simu_enabled(handle)),
            "filter_enabled": bool(dll.licence_core_is_filter_enabled(handle)),
        }

    def evaluation(self) -> dict[str, float | LicenceResult]:
        return {
            "result": LicenceResult(self._dll.licence_core_get_result_code(self._handle)),
            "used_days": float(self._dll.licence_core_get_used_days(self._handle)),
            "remaining_days": float(self._dll.licence_core_get_remaining_days(self._handle)),
        }

    def info(self) -> dict[str, object]:
        info = {
            "board_mac": self.board_mac(),
            "auth_time": self.auth_time(),
            "last_use_time": self.last_use_time(),
            "valid_days": self.valid_days(),
            "trial_days": self.trial_days(),
        }
        info.update(self.feature_flags())
        return info

    def result(self) -> LicenceResult:
        return LicenceResult(self._dll.licence_core_get_result_code(self._handle))

