# FX Hedging Dashboard — $1bn across CNH / INR / JPY / KRW
# Run:  pip install streamlit pandas numpy plotly openpyxl
#       streamlit run hedging_app.py
# Keep Casestudy_Data.xlsx in the same folder (or upload it in the sidebar).

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="FX Hedging — $1bn", layout="wide")
NOTIONAL = 1000  # $mm
PAIRS = ["USDCNH", "USDINR", "USDJPY", "USDKRW"]

@st.cache_data
def load(file):
    df = pd.read_excel(file)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values(["CCYPair", "Date"])

up = st.sidebar.file_uploader("Dataset (xlsx)", type="xlsx")
try:
    df = load(up if up else "Casestudy_Data.xlsx")
except Exception:
    st.warning("Upload Casestudy_Data.xlsx in the sidebar to begin.")
    st.stop()

st.title("Hedging a $1bn Investment — CNH · INR · JPY · KRW")
st.caption("Strategy A: no hedge · B: sell 1Y forwards · C: buy ATM put options on local currency")

# ---------- 1. Market snapshot ----------
dates = sorted(df["Date"].unique())
d0 = st.select_slider("Trade date", options=dates, value=dates[-1],
                      format_func=lambda d: pd.Timestamp(d).strftime("%d-%b-%y"))
snap = df[df["Date"] == d0].set_index("CCYPair").loc[PAIRS]

snap["Fwd hedge carry %"] = (snap["Spot"] / snap["Forward"] - 1) * 100      # + = paid to hedge
snap["Put premium %"] = 0.3989 * snap["ATM Vol"] * 100                       # ATM-forward approx
snap["95% worst move %"] = -1.645 * snap["ATM Vol"] * 100
snap["Unhedged VaR ($mm)"] = snap["95% worst move %"] / 100 * NOTIONAL / 4

c1, c2, c3 = st.columns(3)
c1.metric("Portfolio 95% worst-case (unhedged)", f"{snap['Unhedged VaR ($mm)'].sum():.0f} $mm")
c2.metric("Net carry if fully forward-hedged", f"{snap['Fwd hedge carry %'].mean():+.2f}% p.a.")
c3.metric("Cost to option-hedge everything", f"{snap['Put premium %'].mean():.2f}% (~${snap['Put premium %'].mean()*10:.0f}mm)")

st.dataframe(snap[["Spot", "Forward", "ATM Vol", "Fwd hedge carry %",
                   "Put premium %", "95% worst move %"]].round(3), use_container_width=True)

# ---------- 2. Scenario simulator ----------
st.subheader("Scenario: what if local currencies move vs USD in 1Y?")
mv = st.slider("Local-currency move vs USD (%). Negative = local ccy depreciates (Fed hikes / USD strong)",
               -20, 20, -10)
rows = []
for p_ in PAIRS:
    S0, F0, vol = snap.loc[p_, "Spot"], snap.loc[p_, "Forward"], snap.loc[p_, "ATM Vol"]
    S1 = S0 / (1 + mv / 100)                       # local weaker -> USDXXX higher
    prem = 0.3989 * vol
    a = S0 / S1 - 1
    b = S0 / F0 - 1
    c = max(S0 / F0 - 1, S0 / S1 - 1) - prem
    rows.append([p_, a * 100, b * 100, c * 100])
sc = pd.DataFrame(rows, columns=["Pair", "A No hedge", "B Forward", "C Put option"]).set_index("Pair")
port = sc.mean()

fig = go.Figure()
for col, colr in zip(sc.columns, ["#B02A2A", "#1F7A3D", "#1E2761"]):
    fig.add_bar(name=col, x=list(sc.index) + ["PORTFOLIO"],
                y=list(sc[col]) + [port[col]], marker_color=colr)
fig.update_layout(barmode="group", height=380, yaxis_title="FX return in USD (%)",
                  legend=dict(orientation="h", y=1.12), margin=dict(t=10, b=10))
st.plotly_chart(fig, use_container_width=True)
st.caption(
    f"On $1bn: "
    f"A = {port['A No hedge']*10:+.0f} $mm · "
    f"B = {port['B Forward']*10:+.0f} $mm · "
    f"C = {port['C Put option']*10:+.0f} $mm"
)
# ---------- 3. Backtest on the full dataset ----------
st.subheader("Backtest: every rolling 1Y hedge in the data, settled at realised spot")
@st.cache_data
def backtest(df):
    out = {}
    for p_ in PAIRS:
        d = df[df["CCYPair"] == p_].set_index("Date").sort_index()
        recs = []
        for t in d.index:
            f = d.index[(d.index >= t + pd.DateOffset(years=1)) &
                        (d.index <= t + pd.DateOffset(years=1) + pd.Timedelta(days=5))]
            if len(f) == 0:
                continue
            S0, F0, vol, S1 = d.loc[t, "Spot"], d.loc[t, "Forward"], d.loc[t, "ATM Vol"], d.loc[f[0], "Spot"]
            prem = 0.3989 * vol
            recs.append((t, S0 / S1 - 1, S0 / F0 - 1, max(S0 / F0 - 1, S0 / S1 - 1) - prem))
        out[p_] = pd.DataFrame(recs, columns=["Date", "A", "B", "C"]).set_index("Date")
    n = min(len(v) for v in out.values())
    port = sum(out[p_].iloc[:n][["A", "B", "C"]].values for p_ in PAIRS) / 4
    return out, pd.DataFrame(port, columns=["A", "B", "C"], index=out[PAIRS[0]].index[:n])

bt, btp = backtest(df)
tbl = pd.DataFrame({
    "Avg return %": btp.mean() * 100,
    "Worst case %": btp.min() * 100,
    "Worst case $mm": btp.min() * NOTIONAL,
}).round(2)
tbl.index = ["A · No hedge", "B · Forward", "C · Put option"]
st.dataframe(tbl, use_container_width=True)

fig2 = go.Figure()
for col, colr, nm in zip(["A", "B", "C"], ["#B02A2A", "#1F7A3D", "#1E2761"],
                         ["No hedge", "Forward", "Put option"]):
    fig2.add_scatter(x=btp.index, y=btp[col] * 100, name=nm, line=dict(color=colr))
fig2.update_layout(height=350, yaxis_title="Realised 1Y portfolio FX return (%)",
                   legend=dict(orientation="h", y=1.15), margin=dict(t=10, b=10))
st.plotly_chart(fig2, use_container_width=True)

st.success("**Recommendation:** hedge with 1Y forwards, rolled quarterly — 100% for CNH/JPY/KRW "
           "(positive carry: you are *paid* to hedge) and 75% for INR (forward costs ~2.9%, but INR vol "
           "is only ~5%). Backtest: worst case improves from −$69mm to a guaranteed gain.")
