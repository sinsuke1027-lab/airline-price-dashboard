"""PAGE 0 — サマリー: 路線誘致の根拠を1ページで（エグゼクティブサマリー）"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from utils.loader import load_flights, route_summary, latest_flights
from utils.constants import IATA_COLOR

st.set_page_config(page_title="サマリー", layout="wide", page_icon="🗺️")
st.title("HKG発3路線 就航余地サマリー")
st.caption("中部空港（NGO）への路線誘致提案のための根拠ダッシュボード。全ページの結論を1枚で俯瞰できます。")

flights = load_flights()
summary = route_summary(flights)
df_lat  = latest_flights(flights)

summary_avg = (
    summary.groupby(["route_label", "arrival_iata"])
    .agg(
        avg_typical_high =("typical_high",  "mean"),
        avg_typical_low  =("typical_low",   "mean"),
        avg_lowest_price =("lowest_price",  "mean"),
        high_rate        =("price_level",   lambda x: round((x == "high").mean() * 100, 1)),
        high_days        =("price_level",   lambda x: int((x == "high").sum())),
        total_days       =("price_level",   "count"),
        avg_flights      =("total_flights", "mean"),
    )
    .reset_index()
)

direct_ratio = (
    df_lat.groupby("route_label")
    .apply(lambda x: pd.Series({
        "直行便数":   int((x["stops"] == 0).sum()),
        "総便数":     int(len(x)),
        "乗継便数":   int((x["stops"] > 0).sum()),
        "直行便比率": round((x["stops"] == 0).sum() / len(x) * 100, 1),
    }))
    .reset_index()
)
summary_avg = summary_avg.merge(direct_ratio, on="route_label", how="left")

ngo = summary_avg[summary_avg["arrival_iata"] == "NGO"]
kix = summary_avg[summary_avg["arrival_iata"] == "KIX"]

# ── 自動アラート ───────────────────────────────────────────
if not ngo.empty and not kix.empty:
    n, k = ngo.iloc[0], kix.iloc[0]
    msgs = []
    if n["high_rate"] > k["high_rate"]:
        msgs.append(f"高騰率 {n['high_rate']:.0f}% vs KIX {k['high_rate']:.0f}%")
    if n["avg_typical_high"] > k["avg_typical_high"]:
        msgs.append(f"典型価格上限 ¥{n['avg_typical_high']:,.0f} vs KIX ¥{k['avg_typical_high']:,.0f}")
    if n["avg_flights"] < k["avg_flights"]:
        msgs.append(f"便数 {n['avg_flights']:.1f}便/日 vs KIX {k['avg_flights']:.1f}便")
    ngo_lcc = df_lat[(df_lat["arrival_iata"] == "NGO") & (df_lat["carrier_type"] == "LCC")]
    if ngo_lcc.empty:
        msgs.append("LCC未就航（KIXには複数就航）")
    if msgs:
        st.error("🔴 **NGOは3路線中で最も就航余地が大きい** — " + "　／　".join(msgs))
else:
    st.info("NGOまたはKIXのデータがありません。")

st.markdown("---")

# ── KPIカード（3路線横並び） ───────────────────────────────
st.markdown("### 3路線 主要指標")

routes_sorted = sorted(summary_avg["route_label"].unique())
kpi_cols = st.columns(len(routes_sorted))
for col, route in zip(kpi_cols, routes_sorted):
    row = summary_avg[summary_avg["route_label"] == route]
    if row.empty:
        continue
    r = row.iloc[0]
    arr = r["arrival_iata"]
    lcc_cnt = df_lat[(df_lat["arrival_iata"] == arr) & (df_lat["carrier_type"] == "LCC")]["airline"].nunique()
    col.markdown(
        f"<div style='border-left:4px solid {IATA_COLOR.get(arr,'#888')};padding:8px 12px'>"
        f"<b style='font-size:1.1em'>{route}</b><br>"
        f"高騰率: <b>{r['high_rate']:.0f}%</b> （{r['high_days']}/{r['total_days']}日）<br>"
        f"典型上限: <b>¥{r['avg_typical_high']:,.0f}</b><br>"
        f"平均便数: <b>{r['avg_flights']:.1f}便/日</b><br>"
        f"直行便比率: <b>{r['直行便比率']:.0f}%</b><br>"
        f"LCC就航: <b>{lcc_cnt}社</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── 需要シグナル強度 ──────────────────────────────────────
st.markdown("### 需要シグナル強度")
st.caption(
    "「🔴 強」= 便数も少ない（供給不足の可能性高）、"
    "「🟡 中」= 高騰しているが便数は多い（運賃戦略の影響も考慮が必要）"
)

med_f_sig = summary["total_flights"].median()

def _signal(row):
    if row["price_level"] == "high" and row["total_flights"] < med_f_sig:
        return "🔴 強"
    elif row["price_level"] == "high":
        return "🟡 中（要確認）"
    elif row["price_level"] == "typical":
        return "⚪ 標準"
    else:
        return "🟢 低価格"

summary["シグナル"] = summary.apply(_signal, axis=1)

routes_u = sorted(summary["route_label"].unique())
sig_cols = st.columns(len(routes_u))
for i, route in enumerate(routes_u):
    rsub = summary[summary["route_label"] == route]
    cnt_strong  = (rsub["シグナル"] == "🔴 強").sum()
    cnt_caution = (rsub["シグナル"] == "🟡 中（要確認）").sum()
    total       = len(rsub)
    sig_cols[i].metric(
        route,
        f"🔴 強: {cnt_strong}/{total}件",
        delta=f"🟡 要確認: {cnt_caution}件",
        delta_color="off",
        help="強=便数少+高騰（供給不足が根拠）、中=高騰のみ（運賃戦略の影響も考慮）",
    )

st.caption("⚠️ 全指標はSerpAPIデータ（HKG発・複数検索日・最大8搭乗日）に基づく参考値です。")
