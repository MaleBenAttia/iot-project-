# ============================================
# ATELIER 10 — Edge Computing
# Traitement local des données capteurs
# Décision PWM sans passer par le cloud
# ============================================

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER      = "192.168.100.214"
PORT        = 1883
TOPIC_SUB   = "smart_lighting/node_01/sensors/#"
TOPIC_PUB   = "smart_lighting/node_01/cmd/pwm"
TOPIC_EDGE  = "smart_lighting/node_01/edge/decision"

print("=" * 55)
print("  EDGE NODE — Smart Lighting (Traitement Local)")
print("=" * 55)

# État local (pas besoin du cloud)
edge_state = {
    "ldr": 100,
    "pir_a": False,
    "pir_b": False,
    "hour": datetime.now().hour,
    "last_decision": None,
    "latency_ms": 0
}

def calcul_pwm_local(state):
    """Logique PWM identique à Node-RED mais exécutée localement"""
    t_start = time.time()

    heure = datetime.now().hour
    ldr   = state["ldr"]
    pir   = state["pir_a"] or state["pir_b"]

    # Même logique que Flow 1 Node-RED
    if ldr >= 80:
        pwm = 0       # Jour → éteint
    elif pir:
        pwm = 100     # Présence → pleine puissance
    elif heure >= 22 or heure <= 5:
        pwm = 20      # Nuit profonde → veille
    else:
        pwm = 50      # Nuit normale → réduit

    latency = round((time.time() - t_start) * 1000, 3)
    return pwm, latency

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[EDGE] Connecté au broker local {BROKER}:{PORT}")
        client.subscribe(TOPIC_SUB)
        print(f"[EDGE] Abonné à {TOPIC_SUB}")
    else:
        print(f"[EDGE] Erreur connexion : {rc}")

def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = json.loads(msg.payload.decode())

    # Mettre à jour l'état local
    if "ldr" in topic:
        edge_state["ldr"] = payload.get("value", 100)

    elif "pir/zone_a" in topic:
        edge_state["pir_a"] = payload.get("detected", False)

    elif "pir/zone_b" in topic:
        edge_state["pir_b"] = payload.get("detected", False)

    # Décision immédiate locale
    pwm, latency = calcul_pwm_local(edge_state)
    edge_state["latency_ms"] = latency

    if pwm != edge_state["last_decision"]:
        edge_state["last_decision"] = pwm

        # Commande PWM locale
        cmd = {"led1": pwm, "led2": pwm, "led3": pwm//2, "led4": pwm//2}
        client.publish(TOPIC_PUB, json.dumps(cmd))

        # Données Edge vers ThingsBoard
        edge_data = {
            "edge_pwm"      : pwm,
            "edge_latency"  : latency,
            "edge_ldr"      : edge_state["ldr"],
            "edge_pir"      : edge_state["pir_a"] or edge_state["pir_b"],
            "edge_mode"     : "LOCAL",
            "edge_status"   : "OK"
        }
        client.publish(TOPIC_EDGE, json.dumps(edge_data))

        heure = datetime.now().strftime("%H:%M:%S")
        print(f"[EDGE] {heure} | LDR={edge_state['ldr']} "
              f"PIR={edge_state['pir_a']} | PWM={pwm}% | "
              f"Latence={latency}ms")

# Lancer le client MQTT Edge
client = mqtt.Client(client_id="edge_node_01")
client.username_pw_set("iotuser", "SmartLight2025")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
print("[EDGE] Démarrage boucle Edge (Ctrl+C pour arrêter)...")
client.loop_forever()
