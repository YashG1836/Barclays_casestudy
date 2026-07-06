# FX Hedging Case Study — $1bn across CNH · INR · JPY · KRW

**Problem:** A US company invests $1bn (250m each) in China, India, Japan, Korea for 1 year. Repatriating back to USD exposes it to FX risk. Which hedge: nothing, forwards, or put options?

**Key insight:** Because US rates exceed JP/CN/KR rates, selling those currencies forward *earns* carry (+3.1% JPY, +2.7% CNH, +0.8% KRW). Only INR costs to hedge (−2.9%). Net: the company is **paid +1.5%/yr to remove risk**.

**Proof:** Backtested all 257 rolling 1Y hedges in the dataset against realised spot:

| Strategy | Avg return | Worst case |
|---|---|---|
| A · No hedge | −2.3% (−$23m) | −6.9% (−$69m) |
| **B · Forwards ✓** | **+1.5% (+$15m)** | **+1.2% (+$12m)** |
| C · Put options | −0.9% (−$9m) | −1.6% (−$16m) |

**Recommendation:** Hedge with 1Y forwards, rolled quarterly — 100% CNH/JPY/KRW, 75% INR. Worst case goes from −$69m to a guaranteed gain.

## Files
- `FX_Hedging_Strategy.pptx` — one-page deck (the submission)
<!-- - `FX_Hedging_Model.xlsx` — live model: Hedge Analysis (formulas), Strategy Backtest, Raw Data -->
- `hedging_app.py` — interactive Streamlit dashboard
- `Casestudy_Data.xlsx` — source data (Jul-24 → Jun-26: spot, 1Y forward, ATM vol)

## Run the app
Link : https://casestudy1billion.streamlit.app/

## Method (brief)
- Fwd hedge carry = Spot/Forward − 1 (positive = paid to hedge)
- Put premium ≈ 0.3989 × vol × √T (ATM-forward approximation)
- Worst case = 95% VaR = 1.645 × vol; backtest settles each hedge at spot 1Y later