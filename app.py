import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =====================================================================
# 1. IDENTITÉ DE L'APP  (tbddel hna smiya, logo u couleurs)
# =====================================================================
APP_NAME = "PROJET IFMIA"
APP_LOGO = "🛡️"
APP_TAGLINE = "Surveillance intelligente et diagnostic du moteur"
COLOR_MAIN = "#00b894"   # couleur principale
COLOR_DARK = "#0a3d62"   # couleur du bandeau (début du dégradé)

COLORS = {"ok": "#2ecc71", "warning": "#f39c12", "critical": "#e74c3c"}
LABELS = {"ok": "État normal", "warning": "Avertissement", "critical": "État critique"}
ICON = {"ok": "🟢", "warning": "🟠", "critical": "🔴"}
RANK = {"ok": 0, "warning": 1, "critical": 2}

st.set_page_config(page_title=APP_NAME, page_icon=APP_LOGO, layout="wide")

st.markdown(
    f"""
<style>
.block-container {{ padding-top: 1.2rem; }}
.eg-header {{
    background: linear-gradient(135deg, {COLOR_DARK}, {COLOR_MAIN});
    padding: 22px 28px; border-radius: 16px; color: white; margin-bottom: 18px;
}}
.eg-header h1 {{ margin: 0; font-size: 2.1rem; color: white; }}
.eg-header p {{ margin: 4px 0 0 0; opacity: .9; }}
.eg-status {{
    padding: 16px 22px; border-radius: 14px; font-size: 1.3rem; font-weight: 700;
    color: white; margin-bottom: 14px;
}}
.eg-card {{
    border-radius: 12px; padding: 12px 16px; border-left: 6px solid #999;
    background: rgba(128,128,128,.10); margin-bottom: 10px;
}}
.eg-card b {{ font-size: .95rem; }}
.eg-card span {{ font-size: .85rem; opacity: .85; }}
</style>
""",
    unsafe_allow_html=True,
)

# =====================================================================
# 2. Capteurs: unité, nominal, bruit, plage normale, plage critique
# =====================================================================
SENSORS = {
    "Température liquide":   ("°C",   90,   0.6,  (80, 100),   (70, 110)),
    "Température radiateur": ("°C",   80,   0.6,  (70, 92),    (60, 105)),
    "Régime moteur":         ("RPM",  2000, 25,   (800, 3500), (600, 5000)),
    "Niveau liquide":        ("%",    85,   0.4,  (60, 100),   (40, 100)),
    "Vibrations":            ("mm/s", 1.5,  0.08, (0, 3.5),    (0, 6)),
    "Pression d'huile":      ("bar",  3.5,  0.05, (2.0, 5.0),  (1.0, 6.0)),
    "Température huile":     ("°C",   95,   0.6,  (80, 115),   (70, 130)),
}
N = 120

FAULTS = {
    "Aucun": None,
    "Coupure de signal": "cut",
    "Court-circuit (valeur bloquée au max)": "short",
    "Dérive progressive (surchauffe)": "drift",
    "Signal bloqué (valeur figée)": "stuck",
}


def simulate(seed, fault_sensor, fault_type):
    rng = np.random.default_rng(seed)
    data = {}
    for name, (unit, nom, noise, _, _) in SENSORS.items():
        s = nom + rng.normal(0, noise, N)
        if name == fault_sensor and fault_type:
            half = N // 2
            if fault_type == "cut":
                s[half:] = np.nan
            elif fault_type == "short":
                s[half:] = nom * 3
            elif fault_type == "drift":
                s[half:] += np.linspace(0, nom * 0.35, N - half)
            elif fault_type == "stuck":
                s[half:] = s[half]
        data[name] = s
    return pd.DataFrame(data)


def diagnose(name, series):
    _, nom, _, ok, crit = SENSORS[name]
    last = series.iloc[-1]
    recent = series.iloc[-15:]
    if np.isnan(recent).all():
        return "critical", "Défaut signal capteur – contrôler le capteur et le câblage."
    if last > crit[1] * 1.5 or last < 0:
        return "critical", "Valeur incohérente – court-circuit possible, contrôler le câblage."
    if recent.std() < 1e-9:
        return "warning", "Signal figé – capteur possiblement bloqué."
    if last < crit[0] or last > crit[1]:
        return "critical", "Valeur critique."
    if last < ok[0] or last > ok[1]:
        return "warning", "Valeur hors plage normale."
    return "ok", "Capteur OK"


def trend_warning(df):
    t = df["Température liquide"].dropna()
    rpm = df["Régime moteur"].dropna()
    if len(t) < 40:
        return None
    slope = np.polyfit(np.arange(40), t.iloc[-40:].values, 1)[0]
    if slope > 0.15 and rpm.iloc[-40:].std() < 100:
        return "Dégradation possible du système de refroidissement – contrôle recommandé."
    return None


def gauge(name, value, state):
    unit, _, _, ok, crit = SENSORS[name]
    vmax = crit[1] * 1.25
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=0 if np.isnan(value) else float(value),
            number={"suffix": f" {unit}", "font": {"size": 22}},
            title={"text": name, "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, vmax]},
                "bar": {"color": COLORS[state]},
                "steps": [
                    {"range": [0, crit[0]], "color": "rgba(231,76,60,.35)"},
                    {"range": [crit[0], ok[0]], "color": "rgba(243,156,18,.35)"},
                    {"range": [ok[0], ok[1]], "color": "rgba(46,204,113,.30)"},
                    {"range": [ok[1], crit[1]], "color": "rgba(243,156,18,.35)"},
                    {"range": [crit[1], vmax], "color": "rgba(231,76,60,.35)"},
                ],
            },
        )
    )
    fig.update_layout(height=210, margin=dict(l=20, r=20, t=50, b=10))
    return fig


# =====================================================================
# 3. Interface
# =====================================================================
st.markdown(
    f'<div class="eg-header"><h1>{APP_LOGO} {APP_NAME}</h1><p>{APP_TAGLINE}</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(f"## {APP_LOGO} {APP_NAME}")
    st.caption("Banc pédagogique – données simulées")
    st.divider()
    st.subheader("⚡ Simulation de défauts")
    fault_sensor = st.selectbox("Capteur ciblé", list(SENSORS))
    fault_label = st.selectbox("Type de défaut", list(FAULTS))
    seed = st.number_input("Graine aléatoire", value=1, step=1)
    st.button("🔄 Régénérer")

df = simulate(int(seed), fault_sensor, FAULTS[fault_label])
results = {n: diagnose(n, df[n]) for n in SENSORS}
global_state = max((r[0] for r in results.values()), key=lambda s: RANK[s])
trend = trend_warning(df)
if trend and global_state == "ok":
    global_state = "warning"

st.markdown(
    f'<div class="eg-status" style="background:{COLORS[global_state]}">'
    f"{ICON[global_state]} {LABELS[global_state]}</div>",
    unsafe_allow_html=True,
)
if trend:
    st.warning(f"📈 {trend}")

tab1, tab2, tab3 = st.tabs(["📊 Surveillance", "🩺 Diagnostic capteurs", "📜 Données"])

with tab1:
    names = list(SENSORS)
    for row in (names[:4], names[4:]):
        cols = st.columns(4)
        for col, n in zip(cols, row):
            col.plotly_chart(
                gauge(n, df[n].iloc[-1], results[n][0]),
                width="stretch",
                key=f"g_{n}",
            )

    choice = st.multiselect(
        "Courbes à afficher", names, default=["Température liquide", "Pression d'huile"]
    )
    fig = go.Figure()
    for c in choice:
        fig.add_trace(go.Scatter(y=df[c], mode="lines", name=c))
    fig.update_layout(height=360, xaxis_title="Temps (échantillons)")
    st.plotly_chart(fig, width="stretch")

with tab2:
    for n, (s, msg) in results.items():
        st.markdown(
            f'<div class="eg-card" style="border-left-color:{COLORS[s]}">'
            f"<b>{ICON[s]} {n}</b><br><span>{msg}</span></div>",
            unsafe_allow_html=True,
        )

with tab3:
    st.dataframe(df.round(2), width="stretch")
    st.download_button("⬇️ Télécharger CSV", df.to_csv(index=False), "engineguard_data.csv")
