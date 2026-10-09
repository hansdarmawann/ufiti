import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Windows API bindings via ctypes (Standard Library)
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    def set_creation_time_windows(file_path: Path, timestamp: float):
        # Convert POSIX timestamp to Windows FILETIME (100-ns intervals since Jan 1, 1601 UTC)
        intervals = int((timestamp + 11644473600) * 10000000)
        ft = FILETIME(intervals & 0xFFFFFFFF, (intervals >> 32) & 0xFFFFFFFF)

        GENERIC_WRITE = 0x40000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

        handle = ctypes.windll.kernel32.CreateFileW(
            str(file_path),
            GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )

        if handle == -1 or handle == wintypes.HANDLE(-1).value:
            return False

        # SetFileTime(hFile, lpCreationTime, lpLastAccessTime, lpLastWriteTime)
        success = ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ft), None, None)
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(success)
else:
    def set_creation_time_windows(file_path: Path, timestamp: float):
        return False

# Matches: YYYY-MM-DDTHH_mm_ss, optional -#### suffix, and any extension
PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2})_(\d{2})_(\d{2})(?:-\d+)?\.[^.]+$")

def update_file_timestamps():
    folder = Path(__file__).resolve().parent
    script_name = Path(__file__).name

    print(f"Target directory: {folder}\n")

    for file_path in folder.iterdir():
        if not file_path.is_file() or file_path.name == script_name:
            continue

        filename = file_path.name
        match = PATTERN.match(filename)

        if match:
            date_part, hour, minute, second = match.groups()
            date_time_str = f"{date_part} {hour}:{minute}:{second}"

            try:
                dt_obj = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
                timestamp = dt_obj.timestamp()

                # 1. Update Date Modified & Date Accessed
                os.utime(file_path, (timestamp, timestamp))

                # 2. Update Date Created (Windows only)
                if sys.platform == "win32":
                    set_creation_time_windows(file_path, timestamp)

                print(f"[SUCCESS] Updated '{filename}' -> {dt_obj}")

            except ValueError as error:
                print(f"[ERROR] Failed to parse date for '{filename}': {error}")

if __name__ == "__main__":
    update_file_timestamps()