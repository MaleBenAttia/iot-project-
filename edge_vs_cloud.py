import time, random, numpy as np
import matplotlib.pyplot as plt

print("=" * 55)
print("  COMPARAISON : EDGE vs CLOUD — Smart Lighting")
print("=" * 55)

N = 50

def calcul_pwm_local(ldr, pir, heure):
    if ldr >= 80: return 0
    elif pir: return 100
    elif heure >= 22 or heure <= 5: return 20
    else: return 50

latences_edge, latences_cloud, latences_nodered = [], [], []

for i in range(N):
    ldr   = random.uniform(0, 100)
    pir   = random.choice([True, False])
    heure = random.randint(0, 23)
    t0 = time.perf_counter()
    calcul_pwm_local(ldr, pir, heure)
    t1 = time.perf_counter()
    latences_edge.append((t1 - t0) * 1000)
    latences_cloud.append(random.uniform(80, 350))
    latences_nodered.append(random.uniform(5, 25))

print(f"\n{'Méthode':<20} {'Min (ms)':<12} {'Max (ms)':<12} {'Moyenne (ms)'}")
print("-" * 60)
print(f"{'Edge (local)':<20} {min(latences_edge):.4f}{'':7} {max(latences_edge):.4f}{'':7} {sum(latences_edge)/N:.4f}")
print(f"{'Node-RED (VM)':<20} {min(latences_nodered):.1f}{'':9} {max(latences_nodered):.1f}{'':9} {sum(latences_nodered)/N:.1f}")
print(f"{'Cloud (distant)':<20} {min(latences_cloud):.1f}{'':9} {max(latences_cloud):.1f}{'':9} {sum(latences_cloud)/N:.1f}")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Atelier 10 — Edge vs Cloud : Latences Smart Lighting", fontsize=13, fontweight='bold')

ax1 = axes[0]
data   = [latences_edge, latences_nodered, latences_cloud]
labels = ['Edge\n(local)', 'Node-RED\n(VM)', 'Cloud\n(distant)']
colors = ['#2ecc71', '#3498db', '#e74c3c']
bp = ax1.boxplot(data, labels=labels, patch_artist=True)
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax1.set_ylabel('Latence (ms)')
ax1.set_title('Distribution des latences')
ax1.set_yscale('log')
ax1.grid(axis='y', alpha=0.3)

ax2 = axes[1]
ax2.plot(range(N), latences_edge,    color='#2ecc71', linewidth=1.5, label='Edge')
ax2.plot(range(N), latences_nodered, color='#3498db', linewidth=1.5, label='Node-RED')
ax2.plot(range(N), latences_cloud,   color='#e74c3c', linewidth=1.5, label='Cloud')
ax2.set_xlabel('Mesure #')
ax2.set_ylabel('Latence (ms)')
ax2.set_title('Latence sur 50 décisions')
ax2.legend()
ax2.grid(alpha=0.3)

ax3 = axes[2]
scenarios  = ['VM tombe', 'Internet coupé', 'Node-RED crash']
edge_ok    = [100, 100, 100]
nodered_ok = [0,   100, 0]
cloud_ok   = [0,   0,   50]
x3 = np.arange(len(scenarios))
w  = 0.25
ax3.bar(x3 - w, edge_ok,    w, label='Edge',     color='#2ecc71', alpha=0.8)
ax3.bar(x3,     nodered_ok, w, label='Node-RED', color='#3498db', alpha=0.8)
ax3.bar(x3 + w, cloud_ok,   w, label='Cloud',    color='#e74c3c', alpha=0.8)
ax3.set_ylabel('Disponibilité (%)')
ax3.set_title('Résilience par scénario de panne')
ax3.set_xticks(x3)
ax3.set_xticklabels(scenarios, fontsize=9)
ax3.set_ylim(0, 120)
ax3.legend()
ax3.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('edge_vs_cloud.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n📸 Graphique sauvegardé : edge_vs_cloud.png")
print("""
  ✅ Edge  : < 1ms   — fonctionne même si VM tombe
  ⚠️  Node-RED : 5–25ms  — dépend de Docker
  ❌ Cloud : 80–350ms — dépend internet
""")
