#!/usr/bin/env python3
"""Apply the Huy Vector C3 board selection to the pinned XiaoZhi source tree."""
from pathlib import Path
import argparse
import subprocess
import sys

EXPECTED_UPSTREAM_COMMIT = "ac6deed3d8e75348475364bf40ad953c6cd48054"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match in {path}, found {count}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()

    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    if actual != EXPECTED_UPSTREAM_COMMIT:
        raise RuntimeError(
            f"Unexpected upstream source {actual}; expected {EXPECTED_UPSTREAM_COMMIT}"
        )

    kconfig = source / "main/Kconfig.projbuild"
    replace_once(
        kconfig,
        "    default BOARD_TYPE_XMINI_C3_V3 if IDF_TARGET_ESP32C3",
        "    default BOARD_TYPE_HUY_VECTOR_C3 if IDF_TARGET_ESP32C3",
        "select Huy Vector C3 as the ESP32-C3 default",
    )
    replace_once(
        kconfig,
        '    config BOARD_TYPE_XMINI_C3_V3\n        bool "Xmini C3 V3"',
        '    config BOARD_TYPE_HUY_VECTOR_C3\n'
        '        bool "Huy Vector C3 (ESP32-C3 SuperMini)"\n'
        '        depends on IDF_TARGET_ESP32C3\n'
        '    config BOARD_TYPE_XMINI_C3_V3\n'
        '        bool "Xmini C3 V3"',
        "add Huy Vector C3 Kconfig choice",
    )

    cmake = source / "main/CMakeLists.txt"
    replace_once(
        cmake,
        'elseif(CONFIG_BOARD_TYPE_XMINI_C3_V3)\n'
        '    set(BOARD_DIR "xmini/c3-v3")',
        'elseif(CONFIG_BOARD_TYPE_HUY_VECTOR_C3)\n'
        '    set(BOARD_DIR "huy-vector-c3")\n'
        '    set(BUILTIN_TEXT_FONT font_noto_sans_basic_14_1)\n'
        '    set(BUILTIN_ICON_FONT font_material_symbols_14_1)\n'
        'elseif(CONFIG_BOARD_TYPE_XMINI_C3_V3)\n'
        '    set(BOARD_DIR "xmini/c3-v3")',
        "add Huy Vector C3 CMake board mapping",
    )

    print("Pinned XiaoZhi source patched for Huy Vector C3.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"patch_upstream: {exc}", file=sys.stderr)
        raise
