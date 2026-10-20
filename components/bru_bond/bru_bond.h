#pragma once

#include "esphome/core/component.h"

#include <esp_gap_ble_api.h>
#include <esp_gattc_api.h>

namespace esphome {
namespace bru_bond {

class BruBond : public Component {
 public:
  void set_address(uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3, uint8_t b4, uint8_t b5);
  void dump_config() override;

  void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param);
  void gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param);

 protected:
  uint8_t address_[6]{};
};

}  // namespace bru_bond
}  // namespace esphome
