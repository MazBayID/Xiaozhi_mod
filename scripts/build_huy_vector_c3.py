#!/usr/bin/env python3
"""Run upstream build.py and enforce the Wi-Fi RF power ceiling after reconfigure."""
from pathlib import Path
import os
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_ROOT = REPO_ROOT.parent / "upstream"
if not UPSTREAM_ROOT.is_dir():
    raise SystemExit(f"Missing pinned upstream checkout: {UPSTREAM_ROOT}")

# Generate only the idle and closed-eye frames before CMake discovers board
# sources. The resulting C++ file is compiled from the board directory.
subprocess.run(
    [sys.executable, str(REPO_ROOT / "scripts/generate_mochi_frames.py")],
    check=True,
)

os.chdir(UPSTREAM_ROOT)
sys.path.insert(0, str(UPSTREAM_ROOT / "scripts"))
import build as upstream_build  # noqa: E402

_original_run_idf = upstream_build._run_idf


def patch_wifi_component() -> None:
    candidates = [
        path for path in (UPSTREAM_ROOT / "managed_components").glob("*esp-wifi-connect*")
        if path.is_dir()
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one resolved esp-wifi-connect component, found: "
            + ", ".join(str(path) for path in candidates)
        )

    component = candidates[0]
    station_path = component / "wifi_station.cc"
    ap_path = component / "wifi_configuration_ap.cc"

    station = station_path.read_text(encoding="utf-8")
    old_defaults = "max_tx_power_ = 0;"
    if station.count(old_defaults) != 2:
        raise RuntimeError("Unexpected esp-wifi-connect WifiStation constructor")
    station = station.replace(old_defaults, "max_tx_power_ = 40;")
    old_close = "        nvs_close(nvs);\n    }\n}"
    if station.count(old_close) != 1:
        raise RuntimeError("Unexpected WifiStation NVS initialization block")
    station = station.replace(
        old_close,
        "        nvs_close(nvs);\n    }\n"
        "    max_tx_power_ = std::max<int8_t>(8, std::min<int8_t>(max_tx_power_, 40));\n"
        "}",
        1,
    )
    old_station_apply = (
        "    if (max_tx_power_ != 0) {\n"
        "        ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(max_tx_power_));\n"
        "    }"
    )
    if station.count(old_station_apply) != 1:
        raise RuntimeError("Unexpected WifiStation startup power application")
    station = station.replace(
        old_station_apply,
        "    ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(max_tx_power_));",
        1,
    )
    station_path.write_text(station, encoding="utf-8")

    ap = ap_path.read_text(encoding="utf-8")
    if "#include <algorithm>" not in ap:
        ap = ap.replace("#include <cstdio>\n", "#include <cstdio>\n#include <algorithm>\n", 1)
    if ap.count("max_tx_power_ = 0;") != 1:
        raise RuntimeError("Unexpected WifiConfigurationAp constructor")
    ap = ap.replace("max_tx_power_ = 0;", "max_tx_power_ = 40;", 1)

    old_ap_load = (
        '        err = nvs_get_i8(nvs, "max_tx_power", &max_tx_power_);\n'
        "        if (err == ESP_OK) {\n"
        '            ESP_LOGI(TAG, "WiFi max tx power from NVS: %d", max_tx_power_);\n'
        "            ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(max_tx_power_));\n"
        "        } else {\n"
        "            esp_wifi_get_max_tx_power(&max_tx_power_);\n"
        "        }"
    )
    new_ap_load = (
        '        err = nvs_get_i8(nvs, "max_tx_power", &max_tx_power_);\n'
        "        if (err != ESP_OK) {\n"
        "            max_tx_power_ = 40;\n"
        "        }\n"
        "        max_tx_power_ = std::max<int8_t>(8, std::min<int8_t>(max_tx_power_, 40));\n"
        '        ESP_LOGI(TAG, "WiFi max tx power capped at: %d", max_tx_power_);\n'
        "        ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(max_tx_power_));"
    )
    if ap.count(old_ap_load) != 1:
        raise RuntimeError("Unexpected Wi-Fi configuration AP NVS power block")
    ap = ap.replace(old_ap_load, new_ap_load, 1)

    old_save = "this_->max_tx_power_ = max_tx_power->valueint;"
    if ap.count(old_save) != 1:
        raise RuntimeError("Unexpected Wi-Fi configuration save handler")
    ap = ap.replace(
        old_save,
        "this_->max_tx_power_ = static_cast<int8_t>(std::max(8, std::min(40, max_tx_power->valueint)));",
        1,
    )
    old_ap_close = (
        "        nvs_close(nvs);\n    }\n}\n\nvoid WifiConfigurationAp::StartWebServer()"
    )
    new_ap_close = (
        "        nvs_close(nvs);\n    }\n"
        "    max_tx_power_ = std::max<int8_t>(8, std::min<int8_t>(max_tx_power_, 40));\n"
        "    ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(max_tx_power_));\n"
        "}\n\nvoid WifiConfigurationAp::StartWebServer()"
    )
    if ap.count(old_ap_close) != 1:
        raise RuntimeError("Unexpected Wi-Fi configuration AP startup tail")
    ap = ap.replace(old_ap_close, new_ap_close, 1)

    ap_path.write_text(ap, encoding="utf-8")
    print(f"Applied Wi-Fi TX power ceiling to {component.name} (40 quarter-dBm units).")


def run_idf_with_wifi_cap(*args, **kwargs):
    _original_run_idf(*args, **kwargs)
    if "reconfigure" in args:
        patch_wifi_component()


upstream_build._run_idf = run_idf_with_wifi_cap
upstream_build.main([
    "huy-vector-c3",
    "--name", "huy-vector-c3",
    "--language", "id-ID",
])
