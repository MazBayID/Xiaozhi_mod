# XiaoZhi firmware — Huy Vector C3

Custom ESP32-C3 SuperMini target reconstructed from the supplied firmware binary and wiring reference, using the original upstream XiaoZhi source.

**Identity note:** “Mochi Mod” is only the name of the supplied pinout template. It is not the board name or firmware identity. The reconstructed board class is HuyVectorC3Board; the firmware board type and build variant are huy-vector-c3.

## Current target

- MCU: ESP32-C3 SuperMini
- Flash: **4 MB**
- Upstream XiaoZhi: v2.5.0
- Pinned upstream commit: ac6deed3d8e75348475364bf40ad953c6cd48054
- ESP-IDF: 6.1
- Firmware language: Indonesian (id-ID)
- Display: SSD1306, 128×64, I2C address auto-detection at 0x3C / 0x3D
- Audio: INMP441 + MAX98357A, full-duplex I2S, 24 kHz
- Touch controls: three active-HIGH TTP223 outputs
- Wi-Fi TX power ceiling: PHY startup cap 10 dBm plus runtime cap at API value 40 (quarter-dBm units), mapped to 8.5 dBm

## Wiring reference (Mochi Mod pinout template)

| Module | Signal | GPIO |
|---|---|---:|
| INMP441 | SCK | 1 |
| INMP441 | WS | 2 |
| INMP441 | SD | 10 |
| INMP441 | L/R | GND (left slot) |
| MAX98357A | BCLK | 1 |
| MAX98357A | LRC | 2 |
| MAX98357A | DIN | 5 |
| TTP223 Prev | OUT | 4 |
| TTP223 Next | OUT | 6 |
| TTP223 OK / Pause / Play | OUT | 7 |
| OLED | SCL | 20 |
| OLED | SDA | 21 |

The MAX98357A SD/EN pin must be held at its enabled level. GPIO2 is an ESP32-C3 strapping pin; ensure the attached circuit does not force an invalid reset-time level. USB Serial/JTAG console is selected to avoid UART0 use on GPIO20/21.

## Button actions

- Prev: speaker volume −5.
- Next: speaker volume +5.
- **OK (Push-to-Talk):** hold to capture speech; release to stop capture and submit the audio for an AI response. This behavior is always enabled and does not depend on an MCP setting.
- The OK button no longer uses click/long-press actions for chat toggling or Wi-Fi configuration.

## Wi-Fi transmit-power enforcement

The build wrapper patches the pinned 78/esp-wifi-connect 3.3.1 component after dependency resolution. It clamps the saved value and configuration-page writes to 40 quarter-dBm units, then reapplies the limit whenever Station or configuration AP starts. This prevents a previously saved higher setting from bypassing the board's cap.

## Build

GitHub Actions builds the firmware automatically on pushes and pull requests to main. You can also start a build manually from the Actions tab using Build Huy Vector C3 firmware → Run workflow.

The workflow checks out the exact upstream commit, overlays the board implementation, applies the Wi-Fi power patch, builds with ESP-IDF 6.1, checks the merged image against 4 MiB, and uploads:

- merged-binary.bin — complete merged flash image, write at offset 0x0
- bootloader.bin
- partition-table.bin
- sdkconfig

The 4 MB partition layout uses a factory application partition plus an assets partition; it does not contain two OTA app slots. The merged image must be no larger than 4,194,304 bytes.

## Validation status

A successful CI build does not replace physical testing. The actual board still needs checks for boot reliability, OLED orientation, microphone capture, speaker output, touch response, Wi-Fi connection, and AI conversation.

## Upstream

- XiaoZhi ESP32: https://github.com/78/xiaozhi-esp32
- Baseline tag: v2.5.0
- Baseline commit: ac6deed3d8e75348475364bf40ad953c6cd48054
