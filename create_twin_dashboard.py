#!/usr/bin/env python3
import requests, json, uuid as uuidlib, sys

URL       = "http://localhost:9090"
USER      = "tenant@thingsboard.org"
PASS      = "tenant"
DEVICE_ID = "f899bcf0-3a47-11f1-8159-3bc305173aa3"

CARD_FQN  = "system.cards.value_card"
GAUGE_FQN = "system.analogue_gauges.speed_gauge_canvas_gauges"
CHART_FQN = "system.time_series_chart"

def uid(): return str(uuidlib.uuid4())

r = requests.post(f"{URL}/api/auth/login", json={"username":USER,"password":PASS})
if r.status_code != 200: sys.exit(f"❌ {r.text}")
H = {"X-Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}
print("✅ Authentifié")

AID = uid()

def ds(key, label, color="#2196f3"):
    return {"type":"entity","name":"","entityAliasId":AID,
            "dataKeys":[{"name":key,"type":"timeseries","label":label,
                         "color":color,"settings":{},"_hash":0.5}]}

def ds_multi(rows):
    return {"type":"entity","name":"","entityAliasId":AID,
            "dataKeys":[{"name":k,"type":"timeseries","label":l,
                         "color":c,"settings":{},"_hash":0.5}
                        for k,l,c in rows]}

def card(title, key, label, row, col, unit="", sx=3, sy=2):
    return {
        "typeFullFqn":CARD_FQN,"type":"latest",
        "sizeX":sx,"sizeY":sy,"row":row,"col":col,
        "config":{
            "title":title,"showTitle":True,
            "backgroundColor":"#ffffff","color":"rgba(0,0,0,0.87)",
            "padding":"8px","dropShadow":True,"enableFullscreen":True,
            "useDashboardTimewindow":False,"showLegend":False,
            "datasources":[ds(key,label)],
            "settings":{"units":unit,"decimals":1,"showLabel":True,"label":label,
                        "valueFont":{"size":28,"sizeUnit":"px","family":"Roboto","weight":"500"}},
            "titleStyle":{"fontSize":"16px","fontWeight":400},
            "widgetStyle":{},"actions":{}
        }
    }

def gauge(title, key, label, row, col, color="#2196f3", sx=3, sy=3):
    return {
        "typeFullFqn":GAUGE_FQN,"type":"latest",
        "sizeX":sx,"sizeY":sy,"row":row,"col":col,
        "config":{
            "title":title,"showTitle":True,
            "backgroundColor":"#ffffff","color":"rgba(0,0,0,0.87)",
            "padding":"8px","dropShadow":True,"enableFullscreen":True,
            "useDashboardTimewindow":False,"showLegend":False,
            "datasources":[ds(key,label,color)],
            "settings":{
                "minValue":0,"maxValue":100,
                "unitTitle":"%","showUnitTitle":True,
                "colorPlate":"#fff","colorNeedle":color,
                "colorMajorTicks":"#444","colorMinorTicks":"#666",
                "colorTitle":"#888","colorUnits":"#888","colorNumbers":"#444",
                "colorNeedleShadowUp":"rgba(2,255,255,0.2)",
                "colorNeedleShadowDown":"rgba(188,143,143,0.45)",
                "colorBorderOuter":"#ddd","colorBorderOuterEnd":"#aaa",
                "colorBorderMiddle":"#eee","colorBorderMiddleEnd":"#f0f0f0",
                "colorBorderInner":"#fafafa","colorBorderInnerEnd":"#ccc",
                "colorNeedleCircleOuter":"#f0f0f0","colorNeedleCircleOuterEnd":"#ccc",
                "colorNeedleCircleInner":"#e8e8e8","colorNeedleCircleInnerEnd":"#f5f5f5",
                "highlights":[
                    {"from":0,"to":33,"color":"rgba(244,67,54,0.5)"},
                    {"from":33,"to":66,"color":"rgba(255,152,0,0.5)"},
                    {"from":66,"to":100,"color":"rgba(76,175,80,0.5)"}
                ],
                "highlightsWidth":15,"needle":True,"needleShadow":True,
                "needleType":"arrow","needleStart":75,"needleEnd":99,"needleWidth":5,
                "borders":True,"borderInnerWidth":3,"borderMiddleWidth":3,"borderOuterWidth":3,
                "valueBox":True,"valueBoxWidth":100,"valueBoxBorderRadius":2.5,
                "animationTarget":"needle","animationDuration":500,"animationRule":"linear"
            },
            "titleStyle":{"fontSize":"16px","fontWeight":400},
            "widgetStyle":{},"actions":{}
        }
    }

def chart(title, datasources, row, col, sx=6, sy=4, unit=""):
    return {
        "typeFullFqn":CHART_FQN,"type":"timeseries",
        "sizeX":sx,"sizeY":sy,"row":row,"col":col,
        "config":{
            "title":title,"showTitle":True,
            "backgroundColor":"rgba(0,0,0,0)","color":"rgba(0,0,0,0.87)",
            "padding":"0px","dropShadow":True,"enableFullscreen":True,
            "useDashboardTimewindow":True,"showLegend":True,
            "datasources":datasources,
            "timewindow":{"selectedTab":0,
                "realtime":{"realtimeType":0,"timewindowMs":1800000,"interval":10000},
                "aggregation":{"type":"AVG","limit":25000}},
            "settings":{
                "showLegend":True,
                "legendConfig":{"direction":"column","position":"bottom",
                                "showMin":False,"showMax":False,"showAvg":False,
                                "showTotal":False,"showLatest":True},
                "dataZoom":True,"stack":False,
                "yAxis":{"show":True,"label":unit,"position":"left",
                         "showTickLabels":True,"showTicks":True,
                         "showLine":True,"showSplitLines":True},
                "xAxis":{"show":True,"position":"bottom","showTickLabels":True,
                         "showTicks":True,"showLine":True,"showSplitLines":True},
                "yAxes":{"default":{"units":unit,"decimals":1,"show":True,
                                    "position":"left","id":"default","order":0}},
                "background":{"type":"color","color":"#fff","overlay":{"enabled":False}},
                "padding":"12px","animation":{"animation":True}
            },
            "titleStyle":{"fontSize":"16px","fontWeight":400},
            "widgetStyle":{},"actions":{},"configMode":"basic"
        }
    }

W = {}

# ── Ligne 0 : Statut Twin ──────────────────────────────────────────────────
W[uid()] = card("🟢 Statut Twin",      "twin_status",       "Statut",   0, 0)
W[uid()] = card("⚡ PWM Virtuel",      "twin_pwm",          "PWM",      0, 3, unit="%")
W[uid()] = card("💡 Écart Réel/Twin",  "twin_deviation_pct","Écart",    0, 6, unit="%")
W[uid()] = card("🌿 Économie Énergie", "twin_energy_saving_pct","Saving",0, 9, unit="%")

# ── Ligne 2 : Jauges ──────────────────────────────────────────────────────
W[uid()] = gauge("🏥 Score Santé",     "twin_health_score", "Santé",    2, 0, color="#4caf50")
W[uid()] = gauge("🤖 PWM IA Prédit",   "twin_ai_pwm",       "PWM IA",   2, 3, color="#00bcd4")
W[uid()] = gauge("⚠️ Confiance IA",    "twin_confidence",   "Confiance",2, 6, color="#ff9800")

# ── Ligne 5 : Graphiques Réel vs Twin ────────────────────────────────────
W[uid()] = chart("📊 Consommation : Réel vs Twin",
    [ds_multi([
        ("total_watts",      "Réel (W)",  "#f44336"),
        ("twin_total_watts", "Twin (W)",  "#2196f3"),
    ])], 5, 0, sx=6, sy=4, unit="W")

W[uid()] = chart("🔄 PWM : Réel vs Twin vs IA",
    [ds_multi([
        ("pwm_led1",    "PWM Réel",  "#f44336"),
        ("twin_pwm",    "PWM Twin",  "#2196f3"),
        ("twin_ai_pwm", "PWM IA",    "#00bcd4"),
    ])], 5, 6, sx=6, sy=4, unit="%")

# ── Ligne 9 : Anomalie + Cluster ─────────────────────────────────────────
W[uid()] = chart("🚨 Anomalie + Déviation",
    [ds_multi([
        ("twin_anomaly",       "Anomalie",  "#f44336"),
        ("twin_deviation_pct", "Déviation %","#ff9800"),
    ])], 9, 0, sx=6, sy=4)

W[uid()] = chart("🔬 Score Santé + Économie",
    [ds_multi([
        ("twin_health_score",      "Santé",   "#4caf50"),
        ("twin_energy_saving_pct", "Économie %","#9c27b0"),
    ])], 9, 6, sx=6, sy=4, unit="%")

print(f"✅ {len(W)} widgets construits")

GRID = {
    "backgroundColor":"#eeeeee","color":"rgba(0,0,0,0.870588)",
    "columns":24,"backgroundSizeMode":"100%",
    "autoFillHeight":True,"mobileAutoFillHeight":False,
    "mobileRowHeight":70,"margin":10,"outerMargin":True,"layoutType":"default"
}

lw = {wid: {"sizeX":w["sizeX"],"sizeY":w["sizeY"],"row":w["row"],"col":w["col"]}
      for wid,w in W.items()}

dashboard = {
    "title": "Digital Twin – Smart Lighting Node 01",
    "configuration": {
        "widgets": W,
        "entityAliases": {
            AID: {
                "id":AID,"alias":"SmartLightTwin",
                "filter":{
                    "type":"singleEntity","resolveMultiple":False,
                    "singleEntity":{"entityType":"DEVICE","id":DEVICE_ID}
                }
            }
        },
        "states": {
            "default": {
                "name":"Digital Twin","root":True,
                "layouts":{"main":{"widgets":lw,"gridSettings":GRID}}
            }
        },
        "timewindow": {
            "selectedTab":0,"hideAggregation":False,"hideAggInterval":False,
            "realtime":{"interval":1000,"timewindowMs":60000},
            "aggregation":{"type":"AVG","limit":25000}
        },
        "settings": {
            "stateControllerId":"entity","showTitle":False,
            "showDashboardsSelect":True,"showEntitiesSelect":True,
            "showDashboardTimewindow":True,"showDashboardExport":True,
            "toolbarAlwaysOpen":True,"titleColor":"rgba(0,0,0,0.870588)","showFilters":True
        },
        "filters":{}
    }
}

print("🏗️  Création du Dashboard Digital Twin...")
resp = requests.post(f"{URL}/api/dashboard", headers=H, json=dashboard)
if resp.status_code == 200:
    nid = resp.json()["id"]["id"]
    print(f"\n{'='*60}")
    print(f"✅ Dashboard Digital Twin créé !")
    print(f"🌐 {URL}/dashboards/{nid}")
    print(f"{'='*60}")
else:
    print(f"❌ Erreur {resp.status_code}: {resp.text[:300]}")
