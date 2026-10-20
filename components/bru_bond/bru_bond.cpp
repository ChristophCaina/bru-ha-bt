#include "bru_bond.h"

#include "esphome/core/log.h"

#include <cstring>

namespace esphome {
namespace bru_bond {

static const char *const TAG = "bru_bond";

static uint8_t g_address[6];
static bool g_address_set;
static bool g_encryption_started;

static bool is_bru(const uint8_t *address) {
  return g_address_set && address != nullptr && std::memcmp(address, g_address, sizeof(g_address)) == 0;
}

void BruBond::set_address(uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3, uint8_t b4, uint8_t b5) {
  uint8_t address[6] = {b0, b1, b2, b3, b4, b5};
  std::memcpy(this->address_, address, sizeof(address));
  std::memcpy(g_address, address, sizeof(address));
  g_address_set = true;
}

void BruBond::dump_config() {
  ESP_LOGCONFIG(TAG, "BRU bond:");
  ESP_LOGCONFIG(TAG, "  Address: %02X:%02X:%02X:%02X:%02X:%02X", this->address_[0], this->address_[1],
                this->address_[2], this->address_[3], this->address_[4], this->address_[5]);
}

void BruBond::gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param) {
  // Every client interface receives the same connection event.
  (void) gattc_if;
  if (event == ESP_GATTC_DISCONNECT_EVT) {
    if (is_bru(param->disconnect.remote_bda)) {
      g_encryption_started = false;
    }
    return;
  }
  if (event != ESP_GATTC_CONNECT_EVT && event != ESP_GATTC_OPEN_EVT) {
    return;
  }
  uint8_t *remote = event == ESP_GATTC_CONNECT_EVT ? param->connect.remote_bda : param->open.remote_bda;
  if (!is_bru(remote) || g_encryption_started) {
    return;
  }
  if (event == ESP_GATTC_OPEN_EVT && param->open.status != ESP_GATT_OK && param->open.status != ESP_GATT_ALREADY_OPEN) {
    return;
  }
  ESP_LOGI(TAG, "Starting encryption");
  esp_err_t error = esp_ble_set_encryption(remote, ESP_BLE_SEC_ENCRYPT_MITM);
  if (error != ESP_OK) {
    ESP_LOGW(TAG, "esp_ble_set_encryption failed: %d", error);
  }
}

void BruBond::gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param) {
  if (event != ESP_GAP_BLE_NC_REQ_EVT) {
    return;
  }
  esp_ble_sec_key_notif_t &request = param->ble_security.key_notif;
  if (!is_bru(request.bd_addr)) {
    return;
  }
  ESP_LOGI(TAG, "Accepting code %06lu", static_cast<unsigned long>(request.passkey));
  esp_err_t error = esp_ble_confirm_reply(request.bd_addr, true);
  if (error != ESP_OK) {
    ESP_LOGW(TAG, "esp_ble_confirm_reply failed: %d", error);
  }
}

}  // namespace bru_bond
}  // namespace esphome

// The proxy asks for medium connection parameters as soon as service
// discovery finishes, and the machine drops the link. It also calls
// set_encryption again when Home Assistant catches up. Both go through
// these wrappers so this address stays on the opening parameters and the
// second encryption request does not fail the one already running.
// ponytail: every update for this address is dropped, including after the
// bond. A brew is a short connection; restore medium params if the proxy
// radio starves while the machine stays connected.

extern "C" esp_err_t __real_esp_ble_gap_update_conn_params(esp_ble_conn_update_params_t *params);
extern "C" esp_err_t __wrap_esp_ble_gap_update_conn_params(esp_ble_conn_update_params_t *params) {
  if (params != nullptr && esphome::bru_bond::is_bru(params->bda)) {
    ESP_LOGD("bru_bond", "Skipping connection parameter update");
    return ESP_OK;
  }
  return __real_esp_ble_gap_update_conn_params(params);
}

extern "C" esp_err_t __real_esp_ble_set_encryption(esp_bd_addr_t bd_addr, esp_ble_sec_act_t sec_act);
extern "C" esp_err_t __wrap_esp_ble_set_encryption(esp_bd_addr_t bd_addr, esp_ble_sec_act_t sec_act) {
  if (!esphome::bru_bond::is_bru(bd_addr)) {
    return __real_esp_ble_set_encryption(bd_addr, sec_act);
  }
  if (esphome::bru_bond::g_encryption_started) {
    return ESP_OK;
  }
  esphome::bru_bond::g_encryption_started = true;
  esp_err_t error = __real_esp_ble_set_encryption(bd_addr, ESP_BLE_SEC_ENCRYPT_MITM);
  if (error != ESP_OK) {
    esphome::bru_bond::g_encryption_started = false;
  }
  return error;
}
