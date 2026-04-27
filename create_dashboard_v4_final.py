#!/usr/bin/env python3
"""
Smart Lighting Dashboard — VERSION FINALE CORRIGÉE
Correction clé : préfixe "system." obligatoire sur tous les typeFullFqn en TB 4.x
  system.cards.value_card
  system.analogue_gauges.speed_gauge_canvas_gauges
  system.time_series_chart
"""
import requests, json, uuid as uuidlib, sys

URL       = "http://localhost:9090"
USER      = "tenant@thingsboard.org"
PASS      = "tenant"
DEVICE_ID = "f899bcf0-3a47-11f1-8159-3bc305173aa3"

CARD_FQN  = "system.cards.value_card"
GAUGE_FQN = "system.analogue_gauges.speed_gauge_canvas_gauges"
CHART_FQN = "system.time_series_chart"

def uid(): return str(uuidlib.uuid4())

# ── Auth ──────────────────────────────────────────────────────────────────────
print("🔐 Connexion...")
r = requests.post(f"{URL}/api/auth/login", json={"username": USER, "password": PASS})
if r.status_code != 200:
    sys.exit(f"❌ {r.text}")
H = {"X-Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}
print("✅ Authentifié")

# Supprimer les anciens dashboards "Smart Lighting"
resp = requests.get(f"{URL}/api/tenant/dashboards?limit=50&page=0", headers=H)
for d in resp.json().get("data", []):
    if "Smart Lighting" in d.get("title", ""):
        requests.delete(f"{URL}/api/dashboard/{d['id']['id']}", headers=H)
        print(f"🗑️  Supprimé : {d['title']}")

# ── Entity Alias ──────────────────────────────────────────────────────────────
AID = uid()

def dk(name, label, color="#2196f3", dtype="timeseries"):
    return {
        "name": name, "type": dtype, "label": label,
        "color": color, "settings": {},
        "_hash": round(abs(hash(name)) % 1e6 / 1e6, 6)
    }

def ds(key, label, color="#2196f3"):
    return {"type": "entity", "name": "", "entityAliasId": AID,
            "dataKeys": [dk(key, label, color)]}

def ds_multi(rows):
    return {"type": "entity", "name": "", "entityAliasId": AID,
            "dataKeys": [dk(k, l, c) for k, l, c in rows]}

# ── Widgets ───────────────────────────────────────────────────────────────────
def card(title, key, label, row, col, sx=2, sy=2, unit=""):
    wid = uid()
    return wid, {
        "typeFullFqn": CARD_FQN, "type": "latest",
        "sizeX": sx, "sizeY": sy, "row": row, "col": col,
        "config": {
            "title": title, "showTitle": True,
            "backgroundColor": "#ffffff", "color": "rgba(0,0,0,0.87)",
            "padding": "8px", "dropShadow": True, "enableFullscreen": True,
            "useDashboardTimewindow": False, "showLegend": False,
            "datasources": [ds(key, label)],
            "settings": {
                "labelValueFont": {"size": 12, "sizeUnit": "px", "family": "Roboto",
                                   "weight": "500", "style": "normal"},
                "valueFont": {"size": 28, "sizeUnit": "px", "family": "Roboto",
                              "weight": "500", "style": "normal"},
                "units": unit, "decimals": 1,
                "showLabel": True, "label": label
            },
            "titleStyle": {"fontSize": "16px", "fontWeight": 400},
            "widgetStyle": {}, "actions": {}
        }
    }

def gauge(title, key, label, row, col, color="#2196f3", sx=3, sy=3):
    wid = uid()
    return wid, {
        "typeFullFqn": GAUGE_FQN, "type": "latest",
        "sizeX": sx, "sizeY": sy, "row": row, "col": col,
        "config": {
            "title": title, "showTitle": True,
            "backgroundColor": "#ffffff", "color": "rgba(0,0,0,0.87)",
            "padding": "8px", "dropShadow": True, "enableFullscreen": True,
            "useDashboardTimewindow": False, "showLegend": False,
            "datasources": [ds(key, label, color)],
            "settings": {
                "minValue": 0, "maxValue": 100,
                "unitTitle": "%", "showUnitTitle": True,
                "colorPlate": "#fff",
                "colorMajorTicks": "#444", "colorMinorTicks": "#666",
                "colorTitle": "#888", "colorUnits": "#888",
                "colorNumbers": "#444", "colorNeedle": color,
                "colorNeedleShadowUp": "rgba(2,255,255,0.2)",
                "colorNeedleShadowDown": "rgba(188,143,143,0.45)",
                "colorBorderOuter": "#ddd", "colorBorderOuterEnd": "#aaa",
                "colorBorderMiddle": "#eee", "colorBorderMiddleEnd": "#f0f0f0",
                "colorBorderInner": "#fafafa", "colorBorderInnerEnd": "#ccc",
                "colorNeedleCircleOuter": "#f0f0f0",
                "colorNeedleCircleOuterEnd": "#ccc",
                "colorNeedleCircleInner": "#e8e8e8",
                "colorNeedleCircleInnerEnd": "#f5f5f5",
                "highlights": [
                    {"from": 0,  "to": 33,  "color": "rgba(76,175,80,0.5)"},
                    {"from": 33, "to": 66,  "color": "rgba(255,152,0,0.5)"},
                    {"from": 66, "to": 100, "color": "rgba(244,67,54,0.5)"}
                ],
                "highlightsWidth": 15,
                "needle": True, "needleShadow": True,
                "needleType": "arrow", "needleStart": 75, "needleEnd": 99,
                "needleWidth": 5, "borders": True,
                "borderInnerWidth": 3, "borderMiddleWidth": 3, "borderOuterWidth": 3,
                "valueBox": True, "valueBoxWidth": 100, "valueBoxBorderRadius": 2.5,
                "animationTarget": "needle", "animationDuration": 500,
                "animationRule": "linear"
            },
            "titleStyle": {"fontSize": "16px", "fontWeight": 400},
            "widgetStyle": {}, "actions": {}
        }
    }

def chart(title, datasources, row, col, sx=6, sy=4, unit=""):
    wid = uid()
    return wid, {
        "typeFullFqn": CHART_FQN, "type": "timeseries",
        "sizeX": sx, "sizeY": sy, "row": row, "col": col,
        "config": {
            "title": title, "showTitle": True,
            "backgroundColor": "rgba(0,0,0,0)", "color": "rgba(0,0,0,0.87)",
            "padding": "0px", "dropShadow": True, "enableFullscreen": True,
            "useDashboardTimewindow": True, "showLegend": True,
            "datasources": datasources,
            "timewindow": {
                "selectedTab": 0,
                "realtime": {"realtimeType": 0, "timewindowMs": 1800000,
                             "interval": 10000},
                "aggregation": {"type": "AVG", "limit": 25000}
            },
            "settings": {
                "showLegend": True,
                "legendConfig": {"direction": "column", "position": "bottom",
                                 "sortDataKeys": False, "showMin": False,
                                 "showMax": False, "showAvg": False,
                                 "showTotal": False, "showLatest": True},
                "dataZoom": True, "stack": False,
                "yAxis": {"show": True, "label": unit,
                          "position": "left", "showTickLabels": True,
                          "showTicks": True, "showLine": True,
                          "showSplitLines": True},
                "xAxis": {"show": True, "position": "bottom",
                          "showTickLabels": True, "showTicks": True,
                          "showLine": True, "showSplitLines": True},
                "yAxes": {"default": {"units": unit, "decimals": 1,
                                      "show": True, "position": "left",
                                      "id": "default", "order": 0}},
                "background": {"type": "color", "color": "#fff",
                               "overlay": {"enabled": False}},
                "padding": "12px", "animation": {"animation": True}
            },
            "titleStyle": {"fontSize": "16px", "fontWeight": 400},
            "widgetStyle": {}, "actions": {},
            "configMode": "basic"
        }
    }

# ── Construction ──────────────────────────────────────────────────────────────
W = {}

# Ligne 0 — Capteurs
for item in [
    card("Luminosité LDR", "ldr_value",   "Luminosité", 0, 0,  unit="lux"),
    card("Mode Nuit/Jour", "is_night",    "Mode",        0, 2),
    card("Statut Lampe",   "lamp_status", "Statut",      0, 4),
]:
    W[item[0]] = item[1]

# Ligne 2 — Jauges PWM × 4
for i, c in enumerate(["#2196f3","#4caf50","#ff9800","#9c27b0"]):
    wid, w = gauge(f"PWM LED {i+1}", f"pwm_led{i+1}", "PWM", 2, i*3, color=c)
    W[wid] = w

# Ligne 5 — Graphiques
wid, w = chart("Consommation Totale", [ds("total_watts","Watts","#f44336")], 5, 0, unit="W")
W[wid] = w
wid, w = chart("Watts par LED",
    [ds_multi([("led1_watts","LED 1","#2196f3"),("led2_watts","LED 2","#4caf50"),
               ("led3_watts","LED 3","#ff9800"),("led4_watts","LED 4","#9c27b0")])],
    5, 6, unit="W")
W[wid] = w

# Ligne 9 — PIR
for key, title, label, col in [
    ("pir_zone_a_detected","PIR Zone A",     "Détection A",0),
    ("pir_zone_b_detected","PIR Zone B",     "Détection B",2),
    ("pir_zone_a_count",   "Passages Zone A","Compteur A", 4),
    ("pir_zone_b_count",   "Passages Zone B","Compteur B", 6),
]:
    wid, w = card(title, key, label, 9, col); W[wid] = w

# Ligne 11 — IA
wid, w = gauge("PWM Prédit (IA)","ai_pwm_predicted","PWM IA",11,0,color="#00bcd4"); W[wid]=w
for key, title, label, col in [
    ("ai_anomaly",   "Anomalie IA", "Anomalie", 3),
    ("ai_confidence","Confiance IA","Confiance",5),
    ("ai_cluster",   "Profil Usage","Cluster",  7),
]:
    wid, w = card(title, key, label, 11, col); W[wid] = w

print(f"✅ {len(W)} widgets construits")

# ── Layout ────────────────────────────────────────────────────────────────────
GRID = {
    "backgroundColor": "#eeeeee", "color": "rgba(0,0,0,0.870588)",
    "columns": 24, "backgroundSizeMode": "100%",
    "autoFillHeight": True, "mobileAutoFillHeight": False,
    "mobileRowHeight": 70, "margin": 10, "outerMargin": True,
    "layoutType": "default"
}
lw = {wid: {"sizeX":w["sizeX"],"sizeY":w["sizeY"],"row":w["row"],"col":w["col"]}
      for wid, w in W.items()}

# ── Payload ───────────────────────────────────────────────────────────────────
dashboard = {
    "title": "Smart Lighting - Node 01 (FINAL)",
    "configuration": {
        "widgets": W,
        "entityAliases": {
            AID: {
                "id": AID, "alias": "SmartLight",
                "filter": {
                    "type": "singleEntity", "resolveMultiple": False,
                    "singleEntity": {"entityType": "DEVICE", "id": DEVICE_ID}
                }
            }
        },
        "states": {
            "default": {
                "name": "Smart Lighting", "root": True,
                "layouts": {"main": {"widgets": lw, "gridSettings": GRID}}
            }
        },
        "timewindow": {
            "selectedTab": 0, "hideAggregation": False, "hideAggInterval": False,
            "realtime": {"interval": 1000, "timewindowMs": 60000},
            "aggregation": {"type": "AVG", "limit": 25000}
        },
        "settings": {
            "stateControllerId": "entity", "showTitle": False,
            "showDashboardsSelect": True, "showEntitiesSelect": True,
            "showDashboardTimewindow": True, "showDashboardExport": True,
            "toolbarAlwaysOpen": True, "titleColor": "rgba(0,0,0,0.870588)",
            "showFilters": True
        },
        "filters": {}
    }
}

# ── Envoi ─────────────────────────────────────────────────────────────────────
print("🏗️  Création du dashboard...")
resp = requests.post(f"{URL}/api/dashboard", headers=H, json=dashboard)

if resp.status_code == 200:
    nid = resp.json()["id"]["id"]
    print(f"\n{'='*55}")
    print(f"✅  Dashboard créé!")
    print(f"🌐  {URL}/dashboards/{nid}")
    print(f"📋  ID : {nid}")
    print(f"{'='*55}")
else:
    print(f"❌ Erreur {resp.status_code}")
    print(resp.text[:500])
