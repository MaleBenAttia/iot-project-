#!/usr/bin/env python3
"""
Digital Twin - Lampadaire Node 01
Version corrigée et simplifiée
"""

import requests, json, uuid as uuidlib, sys

URL = "http://192.168.100.214:9090"
USER = "tenant@thingsboard.org"
PASS = "tenant"

# ==================== TON DEVICE ID ICI ====================
DEVICE_ID = "f899bcf0-3a47-11f1-8159-3bc305173aa3"   # ← Change avec ton vrai ID si différent

def uid():
    return str(uuidlib.uuid4())

# ====================== CONNEXION ======================
print("🔐 Connexion à ThingsBoard...")
r = requests.post(f"{URL}/api/auth/login", json={"username": USER, "password": PASS})
if r.status_code != 200:
    sys.exit(f"❌ Erreur connexion: {r.text}")

H = {"X-Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}
print("✅ Authentifié\n")

# Supprimer anciens dashboards Digital Twin
print("🗑️ Suppression des anciens dashboards...")
resp = requests.get(f"{URL}/api/tenant/dashboards?limit=50&page=0", headers=H)
for d in resp.json().get("data", []):
    if "Digital Twin" in d.get("title", ""):
        requests.delete(f"{URL}/api/dashboard/{d['id']['id']}", headers=H)
        print(f"   Supprimé : {d['title']}")

# ====================== FONCTIONS WIDGETS ======================
def card(title, key, label, row, col, sx=4, sy=2, unit=""):
    wid = uid()
    return wid, {
        "typeFullFqn": "system.cards.value_card",
        "type": "latest",
        "sizeX": sx, "sizeY": sy, "row": row, "col": col,
        "config": {
            "title": title,
            "datasources": [{"type": "entity", "entityAliasId": AID, "dataKeys": [{"name": key, "label": label}]}],
            "settings": {"units": unit, "decimals": 1}
        }
    }

def gauge(title, key, label, row, col, color="#2196f3", sx=3, sy=4):
    wid = uid()
    return wid, {
        "typeFullFqn": "system.analogue_gauges.speed_gauge_canvas_gauges",
        "type": "latest",
        "sizeX": sx, "sizeY": sy, "row": row, "col": col,
        "config": {
            "title": title,
            "datasources": [{"type": "entity", "entityAliasId": AID, "dataKeys": [{"name": key, "label": label, "color": color}]}],
            "settings": {"minValue": 0, "maxValue": 100, "unitTitle": "%"}
        }
    }

# ====================== CONSTRUCTION DASHBOARD ======================
print("🏗️ Création du Digital Twin...")

AID = uid()
W = {}

# Widgets Réel
W[uid()] = card("Luminosité LDR (Réel)", "ldr_value", "LDR", 0, 0, unit="lux")
W[uid()] = card("Statut Lampe", "lamp_status", "Statut", 0, 8)

for i in range(4):
    W[uid()] = gauge(f"PWM LED {i+1} (Réel)", f"pwm_led{i+1}", f"LED {i+1}", 2, i*3, color=["#2196f3","#4caf50","#ff9800","#9c27b0"][i])

W[uid()] = card("Consommation Totale (Réel)", "total_watts", "Watts", 6, 0, unit="W")

# Widgets Simulation (zone droite)
W[uid()] = card("Luminosité LDR (Simulation)", "ldr_value", "LDR", 0, 12, unit="lux")
W[uid()] = card("Statut Simulation", "lamp_status", "Statut", 0, 20)

for i in range(4):
    W[uid()] = gauge(f"PWM LED {i+1} (Simulé)", f"pwm_led{i+1}", f"LED {i+1}", 2, 12 + i*3, color=["#2196f3","#4caf50","#ff9800","#9c27b0"][i])

# Layout
GRID = {"backgroundColor": "#f5f5f5", "columns": 24, "margin": 10}
lw = {wid: {"sizeX": w["sizeX"], "sizeY": w["sizeY"], "row": w["row"], "col": w["col"]} for wid, w in W.items()}

dashboard = {
    "title": "Digital Twin - Lampadaire Node 01 (Réel vs Simulation)",
    "configuration": {
        "widgets": W,
        "entityAliases": {
            AID: {
                "id": AID,
                "alias": "Lampadaire",
                "filter": {"type": "singleEntity", "singleEntity": {"entityType": "DEVICE", "id": DEVICE_ID}}
            }
        },
        "states": {
            "default": {
                "name": "Digital Twin",
                "root": True,
                "layouts": {"main": {"widgets": lw, "gridSettings": GRID}}
            }
        }
    }
}

# ====================== ENVOI ======================
print("📤 Envoi vers ThingsBoard...")
resp = requests.post(f"{URL}/api/dashboard", headers=H, json=dashboard)

if resp.status_code == 200:
    nid = resp.json()["id"]["id"]
    print("\n" + "="*65)
    print("✅ Digital Twin créé avec succès !")
    print(f"🌐 Lien : http://192.168.100.214:9090/dashboards/{nid}")
    print("="*65)
else:
    print(f"❌ Erreur {resp.status_code}")
    print(resp.text[:400])
