#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "display/oled_display.h"
#include "application.h"
#include "button.h"
#include "config.h"
#include "mochi_face_frames.h"

#include <lvgl.h>
#include <esp_timer.h>
#include <esp_random.h>

#include <driver/i2c_master.h>
#include <esp_lcd_panel_io.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>
#include <esp_log.h>

#include <algorithm>

#define TAG "HuyVectorC3Board"

namespace {
alignas(4) uint8_t mochi_canvas_buffer[MOCHI_FACE_WIDTH * MOCHI_FACE_HEIGHT * 2];
}

// The LVGL canvas is an overlay on the existing XiaoZhi UI. It is shown only
// while idle; normal listening/speaking/configuration screens remain upstream.
class MochiOledDisplay : public OledDisplay {
public:
    using OledDisplay::OledDisplay;

    ~MochiOledDisplay() override {
        DisplayLockGuard lock(this);
        if (face_timer_ != nullptr) {
            lv_timer_delete(face_timer_);
            face_timer_ = nullptr;
        }
        if (face_canvas_ != nullptr) {
            lv_obj_delete(face_canvas_);
            face_canvas_ = nullptr;
        }
    }

    void SetupUI() override {
        OledDisplay::SetupUI();
        DisplayLockGuard lock(this);
        if (!lock || height() != 64 || face_canvas_ != nullptr) {
            return;
        }

        face_canvas_ = lv_canvas_create(lv_screen_active());
        lv_canvas_set_buffer(face_canvas_, mochi_canvas_buffer,
                             MOCHI_FACE_WIDTH, MOCHI_FACE_HEIGHT,
                             LV_COLOR_FORMAT_RGB565);
        lv_obj_set_pos(face_canvas_, (width() - MOCHI_FACE_WIDTH) / 2, 0);
        lv_obj_set_style_border_width(face_canvas_, 0, 0);
        lv_obj_set_style_pad_all(face_canvas_, 0, 0);
        lv_canvas_fill_bg(face_canvas_, lv_color_black(), LV_OPA_COVER);
        lv_obj_add_flag(face_canvas_, LV_OBJ_FLAG_HIDDEN);
        face_timer_ = lv_timer_create(OnFaceTimer, 80, this);
        ESP_LOGI(TAG, "Mochi idle face overlay initialized");
    }

    void SetPowerSaveMode(bool on) override {
        display_enabled_ = !on;
        OledDisplay::SetPowerSaveMode(on);
    }

private:
    lv_obj_t* face_canvas_ = nullptr;
    lv_timer_t* face_timer_ = nullptr;
    bool display_enabled_ = true;
    bool idle_visible_ = false;
    bool blink_active_ = false;
    uint32_t next_blink_at_ = 0;
    uint32_t blink_until_ = 0;

    static void OnFaceTimer(lv_timer_t* timer) {
        auto* self = static_cast<MochiOledDisplay*>(lv_timer_get_user_data(timer));
        if (self != nullptr) {
            self->TickFace();
        }
    }

    static uint32_t NowMs() {
        return static_cast<uint32_t>(esp_timer_get_time() / 1000ULL);
    }

    void DrawFrame(const uint8_t* bitmap) {
        lv_canvas_fill_bg(face_canvas_, lv_color_black(), LV_OPA_COVER);
        for (int y = 0; y < MOCHI_FACE_HEIGHT; ++y) {
            const int row = y * MOCHI_FACE_ROW_BYTES;
            for (int x = 0; x < MOCHI_FACE_WIDTH; ++x) {
                const uint8_t mask = static_cast<uint8_t>(0x80U >> (x & 7));
                if ((bitmap[row + (x >> 3)] & mask) != 0) {
                    lv_canvas_set_px(face_canvas_, x, y, lv_color_white(), LV_OPA_COVER);
                }
            }
        }
    }

    void TickFace() {
        if (face_canvas_ == nullptr) {
            return;
        }

        const bool should_show =
            display_enabled_ &&
            Application::GetInstance().GetDeviceState() == kDeviceStateIdle;
        if (!should_show) {
            if (idle_visible_) {
                lv_obj_add_flag(face_canvas_, LV_OBJ_FLAG_HIDDEN);
                idle_visible_ = false;
                blink_active_ = false;
            }
            return;
        }

        const uint32_t now = NowMs();
        if (!idle_visible_) {
            DrawFrame(kMochiIdleFrame);
            lv_obj_remove_flag(face_canvas_, LV_OBJ_FLAG_HIDDEN);
            lv_obj_move_foreground(face_canvas_);
            idle_visible_ = true;
            blink_active_ = false;
            next_blink_at_ = now + 2500U + (esp_random() % 3500U);
            return;
        }

        if (blink_active_ && static_cast<int32_t>(now - blink_until_) >= 0) {
            DrawFrame(kMochiIdleFrame);
            blink_active_ = false;
            next_blink_at_ = now + 2800U + (esp_random() % 3800U);
        } else if (!blink_active_ &&
                   static_cast<int32_t>(now - next_blink_at_) >= 0) {
            DrawFrame(kMochiBlinkFrame);
            blink_active_ = true;
            blink_until_ = now + 140U;
        }
    }
};

class HuyVectorC3Board : public WifiBoard {
private:
    i2c_master_bus_handle_t display_i2c_bus_ = nullptr;
    esp_lcd_panel_io_handle_t display_io_ = nullptr;
    esp_lcd_panel_handle_t display_panel_ = nullptr;
    Display* display_ = nullptr;

    Button prev_button_{BUTTON_PREV_GPIO, true, 1200};
    Button next_button_{BUTTON_NEXT_GPIO, true};
    Button ok_button_{BUTTON_OK_GPIO, true};

    void InitializeDisplay() {
        const i2c_master_bus_config_t bus_config = {
            .i2c_port = I2C_NUM_0,
            .sda_io_num = DISPLAY_I2C_SDA_PIN,
            .scl_io_num = DISPLAY_I2C_SCL_PIN,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .intr_priority = 0,
            .trans_queue_depth = 0,
            .flags = {
                .enable_internal_pullup = 1,
            },
        };

        esp_err_t err = i2c_new_master_bus(&bus_config, &display_i2c_bus_);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "OLED I2C bus init failed: %s", esp_err_to_name(err));
            display_ = new NoDisplay();
            return;
        }

        uint8_t address = 0;
        if (i2c_master_probe(display_i2c_bus_, 0x3C, 1000) == ESP_OK) {
            address = 0x3C;
        } else if (i2c_master_probe(display_i2c_bus_, 0x3D, 1000) == ESP_OK) {
            address = 0x3D;
        }

        if (address == 0) {
            ESP_LOGW(TAG, "SSD1306 not found at 0x3C or 0x3D");
            display_ = new NoDisplay();
            return;
        }

        esp_lcd_panel_io_i2c_config_t io_config = {
            .dev_addr = address,
            .scl_speed_hz = 400 * 1000,
            .control_phase_bytes = 1,
            .dc_bit_offset = 6,
            .lcd_cmd_bits = 8,
            .lcd_param_bits = 8,
            .on_color_trans_done = nullptr,
            .user_ctx = nullptr,
            .flags = {
                .dc_low_on_data = 0,
                .disable_control_phase = 0,
            },
        };

        err = esp_lcd_new_panel_io_i2c(display_i2c_bus_, &io_config, &display_io_);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "SSD1306 panel I/O init failed: %s", esp_err_to_name(err));
            display_ = new NoDisplay();
            return;
        }

        esp_lcd_panel_dev_config_t panel_config = {};
        panel_config.reset_gpio_num = GPIO_NUM_NC;
        panel_config.bits_per_pixel = 1;

        esp_lcd_panel_ssd1306_config_t ssd1306_config = {
            .height = DISPLAY_HEIGHT,
        };
        panel_config.vendor_config = &ssd1306_config;

        err = esp_lcd_new_panel_ssd1306(display_io_, &panel_config, &display_panel_);
        if (err == ESP_OK) {
            err = esp_lcd_panel_reset(display_panel_);
        }
        if (err == ESP_OK) {
            err = esp_lcd_panel_init(display_panel_);
        }
        if (err == ESP_OK) {
            err = esp_lcd_panel_disp_on_off(display_panel_, true);
        }

        if (err != ESP_OK) {
            ESP_LOGE(TAG, "SSD1306 initialization failed: %s", esp_err_to_name(err));
            if (display_panel_ != nullptr) {
                esp_lcd_panel_del(display_panel_);
                display_panel_ = nullptr;
            }
            if (display_io_ != nullptr) {
                esp_lcd_panel_io_del(display_io_);
                display_io_ = nullptr;
            }
            display_ = new NoDisplay();
            return;
        }

        ESP_LOGI(TAG, "SSD1306 initialized at 0x%02X", address);
        display_ = new MochiOledDisplay(
            display_io_,
            display_panel_,
            DISPLAY_WIDTH,
            DISPLAY_HEIGHT,
            DISPLAY_MIRROR_X,
            DISPLAY_MIRROR_Y
        );
    }

    void InitializeButtons() {
        prev_button_.OnClick([this]() {
            if (auto* codec = GetAudioCodec()) {
                codec->SetOutputVolume(std::max(0, codec->output_volume() - 5));
            }
        });

        next_button_.OnClick([this]() {
            if (auto* codec = GetAudioCodec()) {
                codec->SetOutputVolume(std::min(100, codec->output_volume() + 5));
            }
        });

        // Keep Wi-Fi provisioning available without stealing the PTT button.
        prev_button_.OnLongPress([this]() {
            EnterWifiConfigMode();
        });

        // Push-to-talk is always active: press to record, release to submit.
        ok_button_.OnPressDown([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateIdle ||
                app.GetDeviceState() == kDeviceStateSpeaking) {
                ESP_LOGI(TAG, "Push-to-talk: start listening");
                app.StartListening();
            }
        });

        ok_button_.OnPressUp([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateListening) {
                ESP_LOGI(TAG, "Push-to-talk: stop listening and submit");
                app.StopListening();
            }
        });
    }

public:
    HuyVectorC3Board() {
        InitializeDisplay();
        InitializeButtons();
    }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecDuplex audio_codec(
            AUDIO_INPUT_SAMPLE_RATE,
            AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_GPIO_BCLK,
            AUDIO_I2S_GPIO_WS,
            AUDIO_I2S_GPIO_DOUT,
            AUDIO_I2S_GPIO_DIN
        );
        return &audio_codec;
    }

    Display* GetDisplay() override {
        return display_;
    }
};

DECLARE_BOARD(HuyVectorC3Board);
