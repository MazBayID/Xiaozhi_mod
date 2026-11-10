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

    application = source / "main/application.cc"
    replace_once(
        application,
        """    } else if (state == kDeviceStateListening) {
        if (protocol_) {
            protocol_->SendStopListening();
        }
        SetDeviceState(kDeviceStateIdle);
    }
}""",
        """    } else if (state == kDeviceStateConnecting) {
        // PTT may be released while the audio channel is still opening.
        // Returning to idle invalidates the scheduled ContinueOpenAudioChannel()
        // before it can start recording after the user has released the button.
        ESP_LOGI(TAG, "PTT released while connecting; cancel pending listening start");
        SetDeviceState(kDeviceStateIdle);
    } else if (state == kDeviceStateListening) {
        if (protocol_) {
            protocol_->SendStopListening();
        }
        SetDeviceState(kDeviceStateIdle);
    }
}""",
        "cancel PTT start when released during audio-channel connection",
    )
    replace_once(
        application,
        """    if (state == kDeviceStateConnecting || state == kDeviceStateListening ||
        state == kDeviceStateSpeaking) {
        ESP_LOGI(TAG, "Closing audio channel due to network disconnection");
        protocol_->CloseAudioChannel();
    }""",
        """    if (state == kDeviceStateConnecting || state == kDeviceStateListening ||
        state == kDeviceStateSpeaking) {
        ESP_LOGI(TAG, "Closing audio channel due to network disconnection");
        if (protocol_ != nullptr && protocol_->IsAudioChannelOpened()) {
            protocol_->CloseAudioChannel();
        }
        // Do not leave the UI/audio state stuck in an active conversation.
        // The next PTT press will open a fresh channel after Wi-Fi reconnects.
        SetDeviceState(kDeviceStateIdle);
    }""",
        "guard protocol close and recover application state after network loss",
    )

    mqtt = source / "main/protocols/mqtt_protocol.cc"
    replace_once(
        mqtt,
        """        if (on_disconnected_ != nullptr) {
            on_disconnected_();
        }
        ESP_LOGI(TAG, "MQTT disconnected, schedule reconnect in %d seconds",
                 MQTT_RECONNECT_INTERVAL_MS / 1000);
        esp_timer_start_once(reconnect_timer_, MQTT_RECONNECT_INTERVAL_MS * 1000);""",
        """        // A broker disconnect invalidates the active UDP audio session.
        // Close it so Application can return Listening/Speaking to Idle.
        CloseAudioChannel(false);
        if (on_disconnected_ != nullptr) {
            on_disconnected_();
        }
        ESP_LOGI(TAG, "MQTT disconnected, schedule reconnect in %d seconds",
                 MQTT_RECONNECT_INTERVAL_MS / 1000);
        esp_timer_stop(reconnect_timer_);
        esp_timer_start_once(reconnect_timer_, MQTT_RECONNECT_INTERVAL_MS * 1000);""",
        "close stale UDP audio session when MQTT disconnects",
    )
    replace_once(
        mqtt,
        """                if (app.GetDeviceState() == kDeviceStateIdle) {
                    ESP_LOGI(TAG, "Reconnecting to MQTT server");
                    auto alive = protocol->alive_;  // Capture alive flag
                    app.Schedule([protocol, alive]() {
                        if (*alive) {
                            protocol->StartMqttClient(false);
                        }
                    });
                }""",
        """                auto alive = protocol->alive_;
                if (app.GetDeviceState() != kDeviceStateIdle) {
                    // Retry later; do not replace the MQTT client during an active session.
                    esp_timer_start_once(protocol->reconnect_timer_,
                                         MQTT_RECONNECT_INTERVAL_MS * 1000);
                    return;
                }
                ESP_LOGI(TAG, "Reconnecting to MQTT server");
                app.Schedule([protocol, alive]() {
                    if (!*alive) {
                        return;
                    }
                    auto& current_app = Application::GetInstance();
                    if (current_app.GetDeviceState() != kDeviceStateIdle) {
                        esp_timer_start_once(protocol->reconnect_timer_,
                                             MQTT_RECONNECT_INTERVAL_MS * 1000);
                        return;
                    }
                    if (!protocol->StartMqttClient(false)) {
                        ESP_LOGW(TAG, "MQTT reconnect failed; retry scheduled");
                        esp_timer_start_once(protocol->reconnect_timer_,
                                             MQTT_RECONNECT_INTERVAL_MS * 1000);
                    }
                });""",
        "retain MQTT reconnect retries until device is idle and broker reconnects",
    )

    manifest = source / "main/idf_component.yml"
    replace_once(
        manifest,
        "  78/esp-wifi-connect: ~3.3.1",
        "  78/esp-wifi-connect: ==3.3.1",
        "pin esp-wifi-connect to the version matched by the RF power patch",
    )

    print("Pinned XiaoZhi source patched for Huy Vector C3.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"patch_upstream: {exc}", file=sys.stderr)
        raise
