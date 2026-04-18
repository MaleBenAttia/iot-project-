import paho.mqtt.client as mqtt
import json
import time

# --- Configuration ---
BROKER = "192.168.100.214"
PORT = 1883
USER = "iotuser"
PASS = "SmartLight2025"
LAMP_ID = "LAMP_03"

# --- Topics ---
TOPIC_LDR = f"smart_lighting/{LAMP_ID}/sensors/ldr"
TOPIC_POWER = f"smart_lighting/{LAMP_ID}/sensors/power"

client = mqtt.Client()
client.username_pw_set(USER, PASS)

print(f"Connexion au broker {BROKER}...")
client.connect(BROKER, PORT)

try:
    while True:
        # 1. Simuler Capteur Luminosité (Il fait nuit -> Lux bas)
        ldr_data = {"value": 5.2, "unit": "lux"}
        client.publish(TOPIC_LDR, json.dumps(ldr_data))
        print(f"Sent LDR: {ldr_data}")

        # On attend un peu que Node-RED traite et calcule le PWM (ex: 50%)
        time.sleep(2)

        # 2. Simuler Consommation (35W = Normal pour 50% PWM)
        # Change 35 par 70 pour tester l'alerte de panne !
        pwr_data = {"lampId": LAMP_ID, "pwm": 50, "watts": 35}
        client.publish(TOPIC_POWER, json.dumps(pwr_data))
        print(f"Sent Power: {pwr_data}")

        print("-" * 30)
        time.sleep(10) # Pause avant le prochain cycle

except KeyboardInterrupt:
    print("Arrêt de la simulation.")
    client.disconnect()
