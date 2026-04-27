#!/usr/bin/env python3
import json, time, threading, requests
import paho.mqtt.client as mqtt

VM_IP        = "172.18.0.3"
BROKER_HOST  = VM_IP
BROKER_PORT  = 1883
BROKER_USER  = "iotuser"
BROKER_PASS  = "SmartLight2025"
TB_HOST = "172.18.0.4"
TB_PORT = 1883
TB_TOKEN = "gltyGA7yg3VV0Dc2OFpE"
FLASK_URL    = f"http://{VM_IP}:5000"
TWIN_INTERVAL= 10
LED_MAX_WATT = 17.5
NB_LEDS      = 4

real_state = {
    "ldr_value":500,"is_night":False,
    "pir_a_detected":False,"pir_a_count":0,
    "pir_b_detected":False,"pir_b_count":0,
    "total_watts":0.0
}
twin_state = {}
state_lock = threading.Lock()
tb_client = None

def on_connect_broker(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connecté à Mosquitto")
        client.subscribe("smart_lighting/+/sensors/#", qos=1)
        print("📡 Abonné à smart_lighting/+/sensors/#")
    else:
        print(f"❌ Erreur broker rc={rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except:
        return
    topic = msg.topic
    with state_lock:
        if "ldr" in topic:
            real_state["ldr_value"] = payload.get("value", real_state["ldr_value"])
            real_state["is_night"]  = real_state["ldr_value"] < 80
        elif "pir/zone_a" in topic:
            real_state["pir_a_detected"] = payload.get("detected", False)
            real_state["pir_a_count"]    = payload.get("count_10min", 0)
        elif "pir/zone_b" in topic:
            real_state["pir_b_detected"] = payload.get("detected", False)
            real_state["pir_b_count"]    = payload.get("count_10min", 0)
        elif "power" in topic:
            real_state["total_watts"] = payload.get("total_watts", 0.0)

def on_connect_tb(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connecté à ThingsBoard MQTT")
    else:
        print(f"❌ Erreur ThingsBoard rc={rc}")

def compute_virtual_pwm(ldr, is_night, pir_detected, pir_count):
    hour = time.localtime().tm_hour
    if not is_night:
        return 0
    if pir_detected or pir_count > 2:
        return 100
    if hour >= 22 or hour <= 5:
        return 20
    return 50

def call_ia(ldr, is_night, pir_count, pwm, real_watts, expected_watts):
    now     = time.localtime()
    hour    = now.tm_hour
    dow     = now.tm_wday
    weekend = 1 if dow >= 5 else 0
    ai_pwm, ai_anomaly, ai_conf, ai_cluster = 0.0, False, 0.0, 0
    try:
        r = requests.post(f"{FLASK_URL}/predict", json={
            "hour":hour,"day_of_week":dow,"is_weekend":weekend,
            "ldr_value":ldr,"is_night":int(is_night),"pir_count_10min":pir_count
        }, timeout=3)
        if r.status_code == 200:
            ai_pwm = r.json().get("pwm_predicted", 0.0)
    except:
        pass
    try:
        r = requests.post(f"{FLASK_URL}/anomaly", json={
            "pwm_command":pwm,"current_consumption_w":real_watts,
            "expected_consumption_w":expected_watts,"hour":hour
        }, timeout=3)
        if r.status_code == 200:
            ai_anomaly = r.json().get("anomaly", False)
            ai_conf    = r.json().get("confidence", 0.0)
    except:
        pass
    try:
        r = requests.post(f"{FLASK_URL}/cluster", json={
            "hour":hour,"pir_count_10min":pir_count,
            "ldr_value":ldr,"is_weekend":weekend
        }, timeout=3)
        if r.status_code == 200:
            ai_cluster = r.json().get("cluster", 0)
    except:
        pass
    return ai_pwm, ai_anomaly, ai_conf, ai_cluster

def compute_and_publish():
    with state_lock:
        snap = real_state.copy()
    ldr         = snap["ldr_value"]
    is_night    = snap["is_night"]
    pir_det     = snap["pir_a_detected"] or snap["pir_b_detected"]
    pir_count   = max(snap["pir_a_count"], snap["pir_b_count"])
    real_watts  = snap["total_watts"]

    v_pwm    = compute_virtual_pwm(ldr, is_night, pir_det, pir_count)
    v_led_w  = round((v_pwm / 100) * LED_MAX_WATT, 2)
    v_total  = round(v_led_w * NB_LEDS, 2)

    ai_pwm, ai_anomaly, ai_conf, ai_cluster = call_ia(
        ldr, is_night, pir_count, v_pwm, real_watts, v_total)

    deviation = round(abs(real_watts - v_total) / v_total * 100, 1) if v_total > 0 else 0.0
    health    = round(max(0.0, 100.0 - deviation - (30.0 if ai_anomaly else 0.0)), 1)
    baseline  = LED_MAX_WATT * NB_LEDS
    saving    = round((1 - v_total / baseline) * 100, 1) if baseline > 0 else 0.0
    if ai_anomaly and ai_conf > 0.8:
        status = "ANOMALY"
    elif deviation > 30:
        status = "DEGRADED"
    else:
        status = "OK"

    data = {
        "twin_pwm"              : v_pwm,
        "twin_led1_watts"       : v_led_w,
        "twin_led2_watts"       : v_led_w,
        "twin_led3_watts"       : v_led_w,
        "twin_led4_watts"       : v_led_w,
        "twin_total_watts"      : v_total,
        "twin_ai_pwm"           : round(ai_pwm, 1),
        "twin_anomaly"          : 1 if ai_anomaly else 0,
        "twin_confidence"       : round(ai_conf, 3),
        "twin_cluster"          : ai_cluster,
        "twin_deviation_pct"    : deviation,
        "twin_health_score"     : health,
        "twin_energy_saving_pct": saving,
        "twin_status"           : status,
        "twin_last_update"      : int(time.time()),
    }

    if tb_client and tb_client.is_connected():
        tb_client.publish("v1/devices/me/telemetry", json.dumps(data), qos=1)
        print(f"📤 TB | status={status} pwm={v_pwm}% health={health} saving={saving}%")
    else:
        print("⚠️  ThingsBoard non connecté")

def twin_loop():
    print(f"🔄 Boucle Twin démarrée (intervalle={TWIN_INTERVAL}s)")
    while True:
        try:
            compute_and_publish()
        except Exception as e:
            print(f"❌ Erreur : {e}")
        time.sleep(TWIN_INTERVAL)

if __name__ == "__main__":
    print("=" * 50)
    print("  🌐 Digital Twin – Smart Lighting Node 01")
    print("=" * 50)

    tb_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="digital-twin-01")
    tb_client.username_pw_set(TB_TOKEN)
    tb_client.on_connect = on_connect_tb
    tb_client.connect(TB_HOST, TB_PORT, keepalive=60)
    tb_client.loop_start()

    broker = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="twin-reader-01")
    broker.username_pw_set(BROKER_USER, BROKER_PASS)
    broker.on_connect = on_connect_broker
    broker.on_message = on_message
    broker.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    broker.loop_start()

    time.sleep(2)
    t = threading.Thread(target=twin_loop, daemon=True)
    t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt Digital Twin")
        broker.loop_stop()
        tb_client.loop_stop()
