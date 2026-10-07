#!/usr/bin/env python3
"""Generate role-specific C headers from one local JSON configuration."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.json"
IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")


def c_string(value):
    return json.dumps(value, ensure_ascii=True)


def nonempty(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}: serve una stringa non vuota")
    return value


def checked_identifier(value, label):
    nonempty(value, label)
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label}: usa solo lettere, numeri, punto, _ o -")
    return value


def checked_topic(value, label):
    nonempty(value, label)
    if any(char in value for char in ("#", "+", "\0", "\n", "\r")) or value.startswith("/"):
        raise ValueError(f"{label}: usa un topic di pubblicazione MQTT senza wildcard")
    if len(value.encode("utf-8")) > 96:
        raise ValueError(f"{label}: massimo 96 byte (limite del client STM32)")
    return value


def main():
    if not CONFIG.exists():
        raise ValueError("config.json assente: copia config.example.json e personalizzalo")
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    wifi, broker, topics, devices = (data[key] for key in ("wifi", "broker", "topics", "devices"))
    ssid = nonempty(wifi["ssid"], "wifi.ssid")
    password = wifi["password"]
    host = nonempty(broker["host"], "broker.host")
    port = broker["port"]
    username = broker["username"]
    broker_password = broker["password"]
    if ssid == "YOUR_WIFI_SSID" or password == "YOUR_WIFI_PASSWORD":
        raise ValueError("sostituisci SSID e password di esempio in config.json")
    if host == "BROKER_LAN_IP_OR_HOSTNAME":
        raise ValueError("sostituisci broker.host con l'indirizzo del tuo broker")
    if not isinstance(password, str) or not isinstance(username, str) or not isinstance(broker_password, str):
        raise ValueError("password e username devono essere stringhe")
    if any(char in value for value in (ssid, password, host) for char in ('"', '\\', '\n', '\r')):
        raise ValueError("SSID, password Wi-Fi e host non possono contenere virgolette, backslash o newline: il bridge usa comandi AT")
    if len(ssid.encode("utf-8")) > 32 or len(password.encode("utf-8")) > 63:
        raise ValueError("SSID massimo 32 byte; password Wi-Fi massimo 63 byte")
    if len(host.encode("utf-8")) > 120:
        raise ValueError("broker.host supera la dimensione del comando AT")
    if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= 65535):
        raise ValueError("broker.port deve essere tra 1 e 65535")
    if broker_password and not username:
        raise ValueError("broker.username è obbligatorio se imposti broker.password")
    names = [checked_identifier(devices[key], f"devices.{key}") for key in (
        "stm32_client_id", "stm32_server_id", "dashboard_id", "device_id")]
    if len(set(names[:3])) != 3:
        raise ValueError("i tre MQTT Client ID devono essere univoci")
    if any(len(name) > 64 for name in names[:3]):
        raise ValueError("MQTT Client ID: massimo 64 caratteri")
    if len(devices["device_id"]) > 16:
        raise ValueError("devices.device_id: massimo 16 caratteri per il payload STM32")
    topic_values = [checked_topic(topics[key], f"topics.{key}") for key in ("sos", "telemetry", "status")]
    if len(set(topic_values)) != 3:
        raise ValueError("i tre topic devono essere distinti")
    common = [
        "/* File generato da tools/configure.py: modifica config.json, non questo file. */",
        "#ifndef DEMO_APP_CONFIG_H",
        "#define DEMO_APP_CONFIG_H",
        f"#define APP_WIFI_SSID {c_string(ssid)}",
        f"#define APP_WIFI_PASSWORD {c_string(password)}",
        f"#define APP_MQTT_BROKER_HOST {c_string(host)}",
        f"#define APP_MQTT_BROKER_PORT {port}U",
        f"#define APP_MQTT_USERNAME {c_string(username)}",
        f"#define APP_MQTT_PASSWORD {c_string(broker_password)}",
        f"#define APP_MQTT_SOS_TOPIC {c_string(topics['sos'])}",
        f"#define APP_MQTT_TELEMETRY_TOPIC {c_string(topics['telemetry'])}",
        f"#define APP_MQTT_STATUS_TOPIC {c_string(topics['status'])}",
        "#define APP_MQTT_KEEP_ALIVE_SEC 30U",
        "#define APP_UART_BAUD 38400U",
    ]
    destinations = {
        "communication/client/include/app_config.h": [
            f"#define APP_MQTT_CLIENT_ID {c_string(devices['stm32_client_id'])}",
            f"#define APP_DEVICE_ID {c_string(devices['device_id'])}",
            "#define APP_TELEMETRY_PERIOD_MS 1000U",
            "#define APP_SENSOR_MAX_AGE_MS 3000U",
        ],
        "communication/server/include/app_config.h": [
            f"#define APP_MQTT_CLIENT_ID {c_string(devices['stm32_server_id'])}",
            "#define APP_MQTT_TOPIC_COUNT 3U",
        ],
        "communication/server/esp8266/neapolis_sos_dashboard/demo_config.h": [
            f"#define APP_MQTT_DASHBOARD_CLIENT_ID {c_string(devices['dashboard_id'])}",
        ],
    }
    for relative, specific in destinations.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(common + specific + ["#endif", ""]), encoding="utf-8")
        print(f"generato: {relative}")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Configurazione non valida: {error}", file=sys.stderr)
        sys.exit(1)
