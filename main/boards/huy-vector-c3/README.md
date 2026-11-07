# Huy Vector C3 board target

This board implementation reconstructs the XiaoZhi v2.5.0 target for an ESP32-C3 SuperMini using the supplied wiring reference. “Mochi Mod” is only the name of the pinout template, not the firmware board identity.

## Hardware mapping

| Device | Signal | ESP32-C3 GPIO |
|---|---|---:|
| INMP441 | SCK | 1 |
| INMP441 | WS | 2 |
| INMP441 | SD | 10 |
| INMP441 | L/R | GND (left channel) |
| MAX98357A | BCLK | 1 |
| MAX98357A | LRC | 2 |
| MAX98357A | DIN | 5 |
| TTP223 Prev | OUT | 4 |
| TTP223 Next | OUT | 6 |
| TTP223 OK | OUT | 7 |
| SSD1306 OLED | SCL | 20 |
| SSD1306 OLED | SDA | 21 |

The OLED driver probes both I2C addresses 0x3C and 0x3D. The TTP223 inputs are configured active-HIGH.

## Button behavior

- Prev: decrease speaker volume by 5.
- Next: increase speaker volume by 5.
- OK click: toggle the XiaoZhi conversation state.
- OK long press: enter Wi-Fi configuration mode.
- If press-to-talk mode is enabled through the built-in MCP tool, holding OK starts listening and releasing it stops listening.

## Audio

The board uses upstream NoAudioCodecDuplex at 24 kHz. BCLK and WS are shared between the INMP441 and MAX98357A; the upstream driver reads the left I2S slot. Tie the INMP441 L/R pin to GND. The MAX98357A SD/EN pin must be held at its enabled level according to the module wiring.

## Wi-Fi transmit power

The build wrapper patches the pinned 78/esp-wifi-connect 3.3.1 component. It clamps the stored/configurable maximum to 40 quarter-dBm units and reapplies that cap on Station and configuration-AP startup. ESP-IDF maps this setting to a supported RF power level below 10 dBm. The config portal cannot raise the cap above this value.

## Flash and partition layout

- Target: ESP32-C3
- Flash: 4 MB
- Partition table: partitions/v2/4m.csv
- This partition map uses a factory app partition and an assets partition; it does not provide dual OTA app slots.

## Build

The repository workflow checks out the exact XiaoZhi v2.5.0 source commit pinned in the top-level README, overlays the board implementation, applies the Wi-Fi power cap, and builds with ESP-IDF 6.1. The build artifact merged-binary.bin is a merged flash image intended to be written at offset 0x0.

The physical wiring, audio levels, OLED orientation, and button behavior still require validation on the actual device.
