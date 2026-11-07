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

- Prev click: decrease speaker volume by 5.
- Hold Prev for 1.2 seconds: enter Wi-Fi configuration mode.
- Next click: increase speaker volume by 5.
- **OK: always-on Push-to-Talk.** Press and hold to start listening; release to stop listening and submit the captured speech for an AI response.
- OK click and long-press actions are intentionally unused, so a long hold cannot accidentally toggle conversation or enter Wi-Fi configuration mode.

## Audio

The board uses upstream NoAudioCodecDuplex at 24 kHz. BCLK and WS are shared between the INMP441 and MAX98357A; the upstream driver reads the left I2S slot. Tie the INMP441 L/R pin to GND. The MAX98357A SD/EN pin must be held at its enabled level according to the module wiring.

## Wi-Fi transmit power

The build sets CONFIG_ESP_PHY_MAX_WIFI_TX_POWER=10 dBm to limit PHY startup power, then patches the pinned 78/esp-wifi-connect 3.3.1 component. It clamps stored/configurable power to 40 quarter-dBm units (mapped to 8.5 dBm) and reapplies that cap on Station and configuration-AP startup. The config portal cannot raise the cap.

## Flash and partition layout

- Target: ESP32-C3
- Flash: 4 MB
- Partition table: partitions/v2/4m.csv
- This partition map uses a factory app partition and an assets partition; it does not provide dual OTA app slots.

## Build

The repository workflow checks out the exact XiaoZhi v2.5.0 source commit pinned in the top-level README, overlays the board implementation, applies the Wi-Fi power cap, and builds with ESP-IDF 6.1. The build artifact merged-binary.bin is a merged flash image intended to be written at offset 0x0.

The physical wiring, audio levels, OLED orientation, and button behavior still require validation on the actual device.
