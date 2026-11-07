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

## Serial diagnostic logs (USB)

The firmware uses ESP-IDF `ESP_LOGI`, `ESP_LOGW`, and `ESP_LOGE` logs. These are sent to the configured ESP-IDF console; they are not shown automatically on the OLED. Board-level messages include OLED initialization and PTT press/release events. XiaoZhi's upstream application also emits connection, listening, and audio-related logs.

### Read logs on Android

1. Connect the ESP32-C3 SuperMini to the Android phone with a **USB data cable** (not a charge-only cable).
2. Install/open an Android USB CDC serial terminal app, for example **Serial USB Terminal** by Kai Morich.
3. Grant the app USB access when Android prompts.
4. Select the ESP32's USB Serial/JTAG (CDC) device. If the app asks for a baud rate, try **115200**; USB CDC itself is not baud-rate limited, but some terminal apps require a value.
5. Clear the terminal, reset the ESP32, and capture the complete startup log.
6. Then test PTT once: hold OK, speak for 2–3 seconds, release OK, and wait about 10 seconds. Save/copy the log from startup through the failed response.

Look for lines containing `HuyVectorC3Board`, `Push-to-talk`, `WiFi`, `websocket`, `listen`, `audio`, `timeout`, or `error`. Send the raw log text, including the first error and several lines before it. Do not share Wi-Fi passwords, access tokens, or other credentials if they appear in the log.

**Important:** Android USB serial access depends on the phone, cable, and terminal app. If the ESP32 does not appear as a USB CDC device, do not change GPIO wiring yet; report the device list/error first. The physical USB connection and serial console still need validation on the actual device.

## Wi-Fi transmit power

The build sets CONFIG_ESP_PHY_MAX_WIFI_TX_POWER=10 dBm to limit PHY startup power, then patches the pinned 78/esp-wifi-connect 3.3.1 component. It clamps stored/configurable power to 40 quarter-dBm units and reapplies that cap on Station and configuration-AP startup. The config portal cannot raise the cap.

## Flash and partition layout

- Target: ESP32-C3
- Flash: 4 MB
- Partition table: partitions/v2/4m.csv
- This partition map uses a factory app partition and an assets partition; it does not provide dual OTA app slots.

## Build

The repository workflow checks out the exact XiaoZhi v2.5.0 source commit pinned in the top-level README, overlays the board implementation, applies the Wi-Fi power cap, and builds with ESP-IDF 6.1. The build artifact merged-binary.bin is a merged flash image intended to be written at offset 0x0.

The physical wiring, audio levels, OLED orientation, button behavior, and USB serial console still require validation on the actual device.
