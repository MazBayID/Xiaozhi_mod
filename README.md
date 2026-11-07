# Xiaozhi Mochi Mod

Custom XiaoZhi AI firmware target for **ESP32-C3 SuperMini**.

> Status: reconstruction in progress. This repository was recreated after the previous source repository was lost. Do not treat this README as confirmation that firmware has been compiled or hardware-tested.

## Hardware

- MCU: ESP32-C3 SuperMini
- Microphone: INMP441
- Audio amplifier: MAX98357A
- Touch inputs: TTP223 (three independent digital outputs)
- Display: I2C OLED (controller/resolution to be confirmed)

## Mochi Mod pinout

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

## Hardware cautions

- **GPIO2 is an ESP32-C3 strapping pin.** Since it is connected to I2S WS/LRC, verify its level during reset/boot and ensure the connected modules do not prevent reliable booting. If boot becomes unreliable, investigate the WS/LRC circuit and consider a pin reassignment.
- **GPIO20/GPIO21 are UART0 RX/TX pins by default.** OLED I2C on these pins can conflict with UART serial logging or console use. USB Serial/JTAG uses separate GPIOs on the C3, but confirm the project's console configuration.
- Confirm the exact ESP32-C3 SuperMini board revision, OLED controller/address, and TTP223 output behavior before finalizing board configuration.
- INMP441 L/R channel-select pin should be tied to the appropriate logic level (commonly GND for left channel); do not leave it floating.
- Power audio amplifier and speaker according to the MAX98357A module specifications; share ground with the ESP32.

## Firmware base

This project is intended to adapt the upstream XiaoZhi ESP32 firmware:

- https://github.com/78/xiaozhi-esp32

Upstream firmware structure, board registration, and SDK requirements change over time. The exact upstream commit and ESP-IDF version must be pinned in project documentation before a reproducible build is claimed.

## Build status

No firmware build or physical-device test has been recorded in this reconstructed repository yet.

## Recovery plan

1. Identify the upstream firmware revision matching the surviving old `.bin`.
2. Recreate the Mochi board definition and pin configuration.
3. Restore custom behavior from old firmware strings, assets, and user recollection.
4. Build for ESP32-C3 and check the binary/partition layout.
5. Flash and validate microphone, speaker, OLED, touch controls, Wi-Fi, and AI interaction on hardware.
