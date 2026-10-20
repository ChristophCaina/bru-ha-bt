import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import esp32_ble
from esphome.const import CONF_ID, CONF_MAC_ADDRESS

DEPENDENCIES = ["bluetooth_proxy"]
CODEOWNERS = ["@saschaludwig"]

bru_bond_ns = cg.esphome_ns.namespace("bru_bond")
BruBond = bru_bond_ns.class_("BruBond", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(BruBond),
        cv.GenerateID(esp32_ble.CONF_BLE_ID): cv.use_id(esp32_ble.ESP32BLE),
        cv.Required(CONF_MAC_ADDRESS): cv.mac_address,
    }
).extend(cv.COMPONENT_SCHEMA)


def _mac_bytes(value):
    text = str(value).replace("-", ":")
    parts = [int(part, 16) for part in text.split(":")]
    if len(parts) != 6 or any(part > 0xFF for part in parts):
        raise cv.Invalid(f"Expected a MAC address, got {value}")
    return parts


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_address(*_mac_bytes(config[CONF_MAC_ADDRESS])))
    parent = await cg.get_variable(config[esp32_ble.CONF_BLE_ID])
    esp32_ble.register_gap_event_handler(parent, var)
    esp32_ble.register_gattc_event_handler(parent, var)
    # Redirect the proxy's post-discovery update and a late pair() call.
    cg.add_build_flag("-Wl,--wrap=esp_ble_gap_update_conn_params")
    cg.add_build_flag("-Wl,--wrap=esp_ble_set_encryption")
