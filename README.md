# XiaoZhi AI ESP32-C3 Reconstruction

Reconstruction of a customized XiaoZhi AI firmware target for **ESP32-C3 SuperMini**, based on a surviving firmware binary and the supplied hardware wiring reference.

> Status: source reconstruction in progress. The old source repository was lost. A matching build and physical-device test have not yet been completed.

## Project identity

- Firmware family: XiaoZhi AI
- Internal board identifier found in the surviving binary: `HuyVectorC3Board`
- Target hardware being reconstructed: ESP32-C3 SuperMini
- **Mochi Mod is only the name of the supplied pinout template.** It is not the board identifier or firmware name.

## Hardware

- MCU: ESP32-C3 SuperMini
- Microphone: INMP441
- Audio amplifier: MAX98357A
- Touch inputs: three TTP223 modules/outputs
- Display: I2C OLED; binary contains strings indicating SSD1306 128x64 support

## Mochi Mod pinout template

The following wiring was supplied as a reference template. It is not yet independently verified against the old source code or physical board.

| Module | Signal | ESP32-C3 GPIO |
|---|---|---:|
| INMP441 | SCK | GPIO1 |
| INMP441 | WS | GPIO2 |
| INMP441 | SD | GPIO10 |
| MAX98357A | BCLK | GPIO1 |
| MAX98357A | LRC | GPIO2 |
| MAX98357A | DIN | GPIO5 |
| TTP223 | Prev | GPIO4 |
| TTP223 | Next | GPIO6 |
| TTP223 | OK / Pause / Play | GPIO7 |
| OLED | SCL | GPIO20 |
| OLED | SDA | GPIO21 |

The microphone and amplifier share I2S clock pins (GPIO1/GPIO2). Firmware must configure a compatible full-duplex/shared-clock I2S audio path.

## Evidence recovered from the old binary

The supplied `.bin` was inspected for embedded strings. It contains, among others:

- Board class/name strings: `HuyVectorC3Board`, `Huy Vector C3 initialized:`
- Touch-control strings: `TTP223 TALK`, `TTP223 NEXT`, `TTP223 MODE`, plus messages referring to `ToggleInfoMode` and `CycleFace`
- Display strings: `SSD1306 128x64`, I2C address probing for `0x3C` and `0x3D`
- Audio-related string: `NoAudioCodecDuplex`
- Framework/service strings: LVGL, WakeNet, MQTT, and WebSocket
- Build metadata strings: firmware version `2.5.0`, ESP-IDF `v6.1`, compile timestamp `Sep 23 2026 02:14:37`

These are binary string observations, **not proof that each feature works** or a complete recovery of the original source. In particular, the TTP223 labels found in the binary do not yet match the supplied Prev/Next/OK naming one-to-one; the intended mapping needs to be reconciled before implementation.

## Hardware cautions

- **GPIO2 is an ESP32-C3 strapping pin.** Since it is connected to I2S WS/LRC, verify its level during reset/boot and ensure the connected modules do not prevent reliable booting. If boot becomes unreliable, investigate the WS/LRC circuit and consider a pin reassignment.
- **GPIO20/GPIO21 are UART0 RX/TX pins by default.** OLED I2C on these pins can conflict with UART serial logging or console use. Confirm the project's console configuration.
- Confirm the exact ESP32-C3 SuperMini board revision, OLED controller/address, and TTP223 output behavior before finalizing board configuration.
- INMP441 L/R channel-select pin should be tied to the appropriate logic level (commonly GND for left channel); do not leave it floating.
- Power the audio amplifier and speaker according to the MAX98357A module specifications; share ground with the ESP32.

## Firmware base

The reconstruction is intended to use the upstream XiaoZhi ESP32 firmware as its base:

- https://github.com/78/xiaozhi-esp32

The exact upstream commit and SDK/toolchain requirements must be pinned before claiming a reproducible build.

## Build status

No source-level firmware build or physical-device test has been completed for this reconstructed repository. The surviving binary has been inspected, but it has not yet been proven reproducible from source.

## Recovery plan

1. Identify the upstream firmware revision closest to the surviving binary.
2. Recreate the `HuyVectorC3Board` board definition while treating the Mochi Mod pinout strictly as a wiring template.
3. Reconcile old binary touch-control behavior with the three supplied TTP223 labels.
4. Restore custom behavior from binary strings, assets, and user recollection.
5. Build for ESP32-C3 and check the binary/partition layout.
6. Flash and validate microphone, speaker, OLED, touch controls, Wi-Fi, and AI interaction on hardware.
