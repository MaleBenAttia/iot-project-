"""
╔══════════════════════════════════════════════════════════════════════╗
║       ESP32 SIMULATOR — Smart Lighting IoT                          ║
║       Hardware simulé : 1x LDR + 2x PIR + 4x LED (PWM)             ║
║       Projet Fédérateur IoT — ISI 2IDISC 2025-2026                  ║
╚══════════════════════════════════════════════════════════════════════╝

TOPICS PUBLIÉS (capteurs → broker) :
  smart_lighting/node_01/sensors/ldr
  smart_lighting/node_01/sensors/pir/zone_a
  smart_lighting/node_01/sensors/pir/zone_b
  smart_lighting/node_01/sensors/power

TOPICS ÉCOUTÉS (broker → ESP32) :
  smart_lighting/node_01/cmd/pwm
  smart_lighting/node_01/cmd/mode

INSTALLATION :
  pip install paho-mqtt

USAGE :
  python esp32_simulator.py                   → mode AUTO (simulation réaliste)
  python esp32_simulator.py --mode nuit       → force scénario nuit
  python esp32_simulator.py --mode jour       → force scénario jour
  python esp32_simulator.py --mode panne      → simule panne LED2
  python esp32_simulator.py --no-tls          → connexion sans TLS (port 1883)
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time
import random
import math
import argparse
import threading
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════
# ⚙️  CONFIGURATION — MODIFIER CES VALEURS SELON TON ENVIRONNEMENT
# ══════════════════════════════════════════════════════════════════════

BROKER_HOST   = "192.168.100.214"   # ← IP de ta VM Ubuntu
BROKER_PORT   = 8883                 # 8883 = MQTTS (TLS) | 1883 = MQTT
NODE_ID       = "node_01"            # Identifiant du nœud

# Authentification MQTT
MQTT_USER     = "iotuser"
MQTT_PASS     = "SmartLight2025"

# Certificats TLS (chemin relatif depuis le dossier du script)
CA_CERT       = "mosquitto/certs/ca.crt"

# Fréquence de publication (secondes)
PUBLISH_INTERVAL = 5

# Puissance max par LED (Watts) — pour calcul conso
MAX_WATTS_PER_LED = 17.5   # 4 LEDs × 17.5W = 70W max total

# ══════════════════════════════════════════════════════════════════════
# 📊 ÉTAT GLOBAL DU SYSTÈME (modifié par les commandes MQTT)
# ══════════════════════════════════════════════════════════════════════

state = {
    # Commandes reçues (PWM 0-100)
    "led1_pwm": 0,
    "led2_pwm": 0,
    "led3_pwm": 0,
    "led4_pwm": 0,

    # Mode de fonctionnement
    "mode": "AUTO",          # AUTO | MANUAL | OFF

    # Scénario de simulation
    "scenario": "auto",      # auto | nuit | jour | panne

    # Compteurs internes
    "cycle": 0,
    "connected": False,
}

# ══════════════════════════════════════════════════════════════════════
# 🌡️  SIMULATION DES CAPTEURS
# ══════════════════════════════════════════════════════════════════════

def simulate_ldr(scenario: str) -> dict:
    """
    Simule le capteur LDR (luminosité ambiante).
    Retourne une valeur en lux selon le scénario.
    
    Référence :
      < 30 lux  → nuit profonde
      30-80 lux → nuit / crépuscule  
      > 80 lux  → jour
    """
    hour = datetime.now().hour

    if scenario == "jour":
        value = random.uniform(200, 800)    # Plein jour
    elif scenario == "nuit":
        value = random.uniform(2, 30)       # Nuit profonde
    elif scenario == "panne":
        value = random.uniform(5, 25)       # Scénario nuit pour voir la panne
    else:
        # Simulation réaliste selon l'heure
        if 6 <= hour <= 8:    # Lever du soleil
            value = random.uniform(50, 200)
        elif 9 <= hour <= 17: # Journée
            value = random.uniform(300, 900) + 50 * math.sin(math.pi * (hour - 9) / 8)
        elif 18 <= hour <= 20: # Coucher du soleil
            value = random.uniform(20, 100)
        else:                  # Nuit (20h-6h)
            value = random.uniform(1, 25)

    # Ajoute un bruit réaliste ±5%
    value = value * random.uniform(0.95, 1.05)

    return {
        "value": round(value, 1),
        "unit": "lux",
        "ts": int(time.time() * 1000)
    }


def simulate_pir(zone: str, scenario: str, cycle: int) -> dict:
    """
    Simule un capteur PIR (détection de présence).
    
    Zone A → contrôle LED1 + LED2 (ex: trottoir gauche)
    Zone B → contrôle LED3 + LED4 (ex: trottoir droit)
    """
    hour = datetime.now().hour

    if scenario == "jour":
        # Jour : beaucoup de passage
        base_prob = 0.7
    elif scenario in ("nuit", "panne"):
        # Nuit : passage rare
        if 23 <= hour or hour <= 4:
            base_prob = 0.05   # Nuit profonde
        else:
            base_prob = 0.25   # Début/fin de nuit
    else:
        # Simulation réaliste selon l'heure
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Heures de pointe
            base_prob = 0.8
        elif 9 <= hour <= 17:    # Journée normale
            base_prob = 0.5
        elif 20 <= hour <= 23:   # Soirée
            base_prob = 0.3
        else:                     # Nuit profonde
            base_prob = 0.05

    # Les deux zones ne détectent pas forcément en même temps
    if zone == "b":
        base_prob *= 0.8  # Zone B légèrement moins active

    detected = random.random() < base_prob

    # Compteur de passages dans les 10 dernières minutes (simulé)
    count = random.randint(1, 8) if detected else random.randint(0, 2)

    return {
        "detected": detected,
        "count_10min": count,
        "zone": zone.upper(),
        "ts": int(time.time() * 1000)
    }


def simulate_power(scenario: str) -> dict:
    """
    Simule la consommation électrique des 4 LEDs.
    Basé sur les commandes PWM reçues + bruit réaliste.
    
    PANNE simulée sur LED2 :
    - Si pwm_cmd > 0 mais watts ≈ 0 → court-circuit / LED grillée
    - Détecté par le nœud Node-RED "Détecteur de panne"
    """
    results = {}
    total = 0.0

    for i, led in enumerate(["led1", "led2", "led3", "led4"], 1):
        pwm = state[f"{led}_pwm"]
        expected_w = (pwm / 100.0) * MAX_WATTS_PER_LED

        # Scénario panne : LED2 ne consomme pas malgré la commande
        if scenario == "panne" and led == "led2":
            actual_w = 0.0   # ← Panne ! LED2 grillée
        else:
            # Bruit réaliste ±8% sur la conso réelle
            noise = random.uniform(0.92, 1.08)
            actual_w = expected_w * noise

        results[f"{led}_watts"] = round(actual_w, 2)
        results[f"{led}_pwm_cmd"] = pwm
        total += actual_w

    results["total_watts"] = round(total, 2)
    results["ts"] = int(time.time() * 1000)
    return results


# ══════════════════════════════════════════════════════════════════════
# 📡 CALLBACKS MQTT
# ══════════════════════════════════════════════════════════════════════

def on_connect(client, userdata, flags, rc):
    codes = {
        0: "✅ Connecté au broker MQTT",
        1: "❌ Version MQTT refusée",
        2: "❌ Client ID rejeté",
        3: "❌ Broker indisponible",
        4: "❌ Identifiants incorrects",
        5: "❌ Non autorisé",
    }
    print(f"\n{codes.get(rc, f'Code inconnu: {rc}')}")

    if rc == 0:
        state["connected"] = True
        # S'abonner aux topics de commande
        client.subscribe(f"smart_lighting/{NODE_ID}/cmd/pwm", qos=1)
        client.subscribe(f"smart_lighting/{NODE_ID}/cmd/mode", qos=1)
        print(f"📥 Abonné aux commandes : smart_lighting/{NODE_ID}/cmd/#\n")


def on_disconnect(client, userdata, rc):
    state["connected"] = False
    if rc != 0:
        print(f"\n⚠️  Déconnexion inattendue (code {rc}). Reconnexion en cours...")


def on_message(client, userdata, msg):
    """Traite les commandes reçues depuis Node-RED."""
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        print(f"⚠️  Payload non-JSON reçu sur {topic}: {msg.payload}")
        return

    if topic.endswith("/cmd/pwm"):
        # ── Commande PWM pour les 4 LEDs ──────────────────────────────
        for led in ["led1", "led2", "led3", "led4"]:
            if led in payload:
                pwm_val = max(0, min(100, int(payload[led])))
                state[f"{led}_pwm"] = pwm_val

        source = payload.get("source", "inconnu")
        print(f"\n{'═'*60}")
        print(f"💡 COMMANDE PWM reçue (source: {source})")
        print(f"   LED1: {state['led1_pwm']}%  |  LED2: {state['led2_pwm']}%")
        print(f"   LED3: {state['led3_pwm']}%  |  LED4: {state['led4_pwm']}%")
        print(f"{'═'*60}")

    elif topic.endswith("/cmd/mode"):
        # ── Changement de mode ────────────────────────────────────────
        new_mode = payload.get("mode", "AUTO").upper()
        state["mode"] = new_mode
        print(f"\n🔧 MODE changé → {new_mode}")

        if new_mode == "OFF":
            for led in ["led1", "led2", "led3", "led4"]:
                state[f"{led}_pwm"] = 0
            print("   Toutes les LEDs éteintes.")


def on_publish(client, userdata, mid):
    pass  # Silencieux — les confirmations sont gérées dans la boucle principale


# ══════════════════════════════════════════════════════════════════════
# 📤 PUBLICATION DES DONNÉES CAPTEURS
# ══════════════════════════════════════════════════════════════════════

def publish_sensors(client: mqtt.Client):
    """Publie tous les capteurs sur leurs topics respectifs."""
    cycle  = state["cycle"]
    scen   = state["scenario"]
    base   = f"smart_lighting/{NODE_ID}/sensors"

    # 1. LDR
    ldr_data = simulate_ldr(scen)
    client.publish(f"{base}/ldr", json.dumps(ldr_data), qos=1)

    # 2. PIR Zone A
    pir_a = simulate_pir("a", scen, cycle)
    client.publish(f"{base}/pir/zone_a", json.dumps(pir_a), qos=1)

    # 3. PIR Zone B
    pir_b = simulate_pir("b", scen, cycle)
    client.publish(f"{base}/pir/zone_b", json.dumps(pir_b), qos=1)

    # 4. Consommation électrique
    power_data = simulate_power(scen)
    client.publish(f"{base}/power", json.dumps(power_data), qos=1)

    # ── Affichage console ─────────────────────────────────────────────
    now = datetime.now().strftime("%H:%M:%S")
    is_night = ldr_data["value"] < 80

    print(f"\n[{now}] Cycle #{cycle}  |  Mode: {state['mode']}  |  "
          f"Scénario: {scen.upper()}")
    print(f"  🌗 LDR    : {ldr_data['value']} lux  → {'🌙 NUIT' if is_night else '☀️  JOUR'}")
    print(f"  👁️  PIR A  : {'🟢 DÉTECTÉ' if pir_a['detected'] else '⚪ aucun'}"
          f"  ({pir_a['count_10min']} passages/10min)")
    print(f"  👁️  PIR B  : {'🟢 DÉTECTÉ' if pir_b['detected'] else '⚪ aucun'}"
          f"  ({pir_b['count_10min']} passages/10min)")
    print(f"  ⚡ Conso   : LED1={power_data['led1_watts']}W  "
          f"LED2={power_data['led2_watts']}W  "
          f"LED3={power_data['led3_watts']}W  "
          f"LED4={power_data['led4_watts']}W  "
          f"→ Total: {power_data['total_watts']}W")
    print(f"  💡 PWM cmd : LED1={state['led1_pwm']}%  "
          f"LED2={state['led2_pwm']}%  "
          f"LED3={state['led3_pwm']}%  "
          f"LED4={state['led4_pwm']}%")

    # Avertissement panne
    if scen == "panne":
        print(f"  ⚠️  PANNE SIMULÉE : LED2 grillée (cmd={state['led2_pwm']}% mais 0W)")

    state["cycle"] += 1


# ══════════════════════════════════════════════════════════════════════
# 🚀 POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Simulateur ESP32 — Smart Lighting IoT"
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "nuit", "jour", "panne"],
        default="auto",
        help="Scénario de simulation (défaut: auto)"
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Connexion sans TLS sur port 1883"
    )
    parser.add_argument(
        "--host",
        default=BROKER_HOST,
        help=f"IP du broker MQTT (défaut: {BROKER_HOST})"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=PUBLISH_INTERVAL,
        help=f"Intervalle de publication en secondes (défaut: {PUBLISH_INTERVAL})"
    )
    args = parser.parse_args()

    state["scenario"] = args.mode
    port = 1883 if args.no_tls else BROKER_PORT

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       ESP32 SIMULATOR — Smart Lighting IoT                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Broker    : {args.host}:{port}")
    print(f"  TLS       : {'❌ Désactivé' if args.no_tls else '✅ Activé (MQTTS)'}")
    print(f"  Nœud      : {NODE_ID}")
    print(f"  Scénario  : {args.mode.upper()}")
    print(f"  Intervalle: {args.interval}s")
    print()

    # ── Création du client MQTT ───────────────────────────────────────
    client = mqtt.Client(client_id=f"esp32-sim-{NODE_ID}", clean_session=True)
    client.username_pw_set(MQTT_USER, MQTT_PASS)

    # Configuration TLS
    if not args.no_tls:
        try:
            client.tls_set(
                ca_certs=CA_CERT,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            print(f"🔒 TLS configuré avec CA : {CA_CERT}")
        except FileNotFoundError:
            print(f"⚠️  Certificat CA non trouvé : {CA_CERT}")
            print("   → Passage automatique en mode sans TLS (port 1883)")
            port = 1883
            client = mqtt.Client(client_id=f"esp32-sim-{NODE_ID}")
            client.username_pw_set(MQTT_USER, MQTT_PASS)

    # Callbacks
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.on_publish    = on_publish

    # Connexion
    print(f"\n🔌 Connexion à {args.host}:{port}...")
    try:
        client.connect(args.host, port, keepalive=60)
    except Exception as e:
        print(f"❌ Impossible de se connecter : {e}")
        print("\n🔧 Vérifications :")
        print("   1. La VM Ubuntu est-elle démarrée ?")
        print("   2. sudo docker ps → iot_mosquitto doit être 'Up'")
        print("   3. L'IP dans BROKER_HOST est-elle correcte ?")
        print("   4. Le port 8883 est-il ouvert ? (sudo ufw status)")
        return

    # ── Boucle principale ─────────────────────────────────────────────
    client.loop_start()   # Thread MQTT en arrière-plan

    print("\n✅ Simulateur démarré. Ctrl+C pour arrêter.\n")
    print(f"{'─'*60}")
    print("📡 Topics publiés :")
    print(f"   smart_lighting/{NODE_ID}/sensors/ldr")
    print(f"   smart_lighting/{NODE_ID}/sensors/pir/zone_a")
    print(f"   smart_lighting/{NODE_ID}/sensors/pir/zone_b")
    print(f"   smart_lighting/{NODE_ID}/sensors/power")
    print(f"\n📥 Topics écoutés :")
    print(f"   smart_lighting/{NODE_ID}/cmd/pwm")
    print(f"   smart_lighting/{NODE_ID}/cmd/mode")
    print(f"{'─'*60}\n")

    try:
        while True:
            if state["connected"]:
                publish_sensors(client)
            else:
                print("⏳ En attente de connexion MQTT...")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n\n{'═'*60}")
        print("🛑 Arrêt du simulateur.")
        print(f"   Total cycles publiés : {state['cycle']}")
        client.loop_stop()
        client.disconnect()
        print("   Déconnecté proprement.")
        print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
