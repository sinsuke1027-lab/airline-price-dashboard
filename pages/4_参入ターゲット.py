"""PAGE 4 — 参入ターゲット: 誰に・何を提案するか（C3 + E2 統合）"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.loader import load_flights, latest_flights, load_aircraft_master, route_summary

st.set_page_config(page_title="参入ターゲット", layout="wide", page_icon="🎯")
st.title("4｜参入ターゲット — 誰に、何を提案するか")
st.caption("未就航航空会社の誘致リスト・増便交渉対象・路線優先度ランキングを一覧します。")

# ── サイドバー ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### フィルター")

flights    = load_flights()
df_lat     = latest_flights(flights)
summary    = route_summary(flights)
aircraft_m = load_aircraft_master()

arrivals = sorted(df_lat["arrival_iata"].unique())

with st.sidebar:
    target_arr = st.selectbox(
        "誘致したい空港（自空港）",
        arrivals,
        index=arrivals.index("NGO") if "NGO" in arrivals else 0,
    )
    ref_options = [a for a in arrivals if a != target_arr]
    ref_arrs = st.multiselect("比較元（競合空港）", ref_options, default=ref_options)

if not ref_arrs:
    st.warning("比較元の空港を選択してください。")
    st.stop()

dep_iata      = df_lat["departure_iata"].mode().iloc[0] if not df_lat.empty else "HKG"
LOAD_FACTOR   = 0.80

ngo_prices    = df_lat[df_lat["arrival_iata"] == target_arr].groupby("flight_date")["route_lowest_price"].first()
avg_ngo_price = ngo_prices.mean() if not ngo_prices.empty else 0
ngo_pl        = df_lat[df_lat["arrival_iata"] == target_arr]["route_price_level"].mode()
ngo_pl_str    = ngo_pl.iloc[0] if not ngo_pl.empty else "不明"
level_label   = {"low": "低価格", "typical": "標準", "high": "高騰"}

target_airlines = set(df_lat[df_lat["arrival_iata"] == target_arr]["airline"].unique())
ref_airlines    = set(df_lat[df_lat["arrival_iata"].isin(ref_arrs)]["airline"].unique())
missing  = sorted(ref_airlines - target_airlines)
present  = sorted(target_airlines & ref_airlines)

# ── KPIカード ──────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("誘致ターゲット数（未就航）", len(missing),
          help=f"{dep_iata}→{target_arr} 未就航・比較元に就航中")
c2.metric(f"{dep_iata}→{target_arr} 平均最安値", f"¥{avg_ngo_price:,.0f}")
c3.metric(f"価格水準", level_label.get(ngo_pl_str, "不明"))
c4.metric("増便交渉対象（既就航）", len(present))

# アラート
if missing:
    lcc_m = [a for a in missing
             if not df_lat[df_lat["airline"] == a]["carrier_type"].empty
             and df_lat[df_lat["airline"] == a]["carrier_type"].iloc[0] == "LCC"]
    fsc_m = [a for a in missing
             if not df_lat[df_lat["airline"] == a]["carrier_type"].empty
             and df_lat[df_lat["airline"] == a]["carrier_type"].iloc[0] == "FSC"]
    ref_str = " / ".join(ref_arrs)
    if fsc_m:
        st.error(f"🔴 **{dep_iata}発FSC未就航（{target_arr}）: {', '.join(fsc_m)}**  "
                 f"— {dep_iata}→{ref_str} には就航済み。同一出発地で実績ありの最優先ターゲット。")
    if lcc_m:
        st.warning(f"⚠️ **{dep_iata}発LCC未就航（{target_arr}）: {', '.join(lcc_m)}**  "
                   f"— LCC参入で価格競争力・旅客数の押し上げ効果が期待できます。")

_med_f_sig4 = summary["total_flights"].median()
_tgt_summary = summary[summary["arrival_iata"] == target_arr]
if not _tgt_summary.empty:
    _strong4  = int(((_tgt_summary["price_level"] == "high") & (_tgt_summary["total_flights"] < _med_f_sig4)).sum())
    _caution4 = int(((_tgt_summary["price_level"] == "high") & (_tgt_summary["total_flights"] >= _med_f_sig4)).sum())
    _total4   = len(_tgt_summary)
    st.caption(
        f"📊 **需要シグナル（{dep_iata}→{target_arr}）**: "
        f"🔴 強（便数少＋高騰）: {_strong4}/{_total4}件 ／ "
        f"🟡 中（高騰のみ）: {_caution4}件 — "
        "詳細は「需要の実証」「市場構造」ページを参照"
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════
# SECTION 1: 誘致ターゲット
# ══════════════════════════════════════════════════════════
st.markdown("## 誘致ターゲット一覧")

tab1, tab2 = st.tabs([
    f"🎯 未就航 — 誘致ターゲット（{len(missing)}社）",
    f"✅ 既就航 — 増便交渉対象（{len(present)}社）",
])

with tab1:
    if not missing:
        st.success("比較元の全航空会社が既に就航しています。")
    else:
        rows = []
        for airline in missing:
            sub = df_lat[(df_lat["airline"] == airline) & (df_lat["arrival_iata"].isin(ref_arrs))]
            if sub.empty:
                continue
            carrier_type   = sub["carrier_type"].iloc[0]
            routes_served  = [f"{dep_iata}→{a}" for a in sub["arrival_iata"].unique()]
            aircraft_used  = sub["aircraft"].mode().iloc[0] if not sub["aircraft"].mode().empty else "不明"
            seats_row      = aircraft_m[aircraft_m["aircraft_name"] == aircraft_used]
            seats          = int(seats_row["seats"].iloc[0]) if not seats_row.empty else None
            body_type      = seats_row["body_type"].iloc[0] if not seats_row.empty else "不明"
            avg_price      = sub["price_jpy"].mean()
            est_rev        = avg_ngo_price * seats * LOAD_FACTOR if seats else None
            rows.append({
                "航空会社":              airline,
                "種別":                 carrier_type,
                f"就航中の路線":         "・".join(routes_served),
                "使用機材":             aircraft_used,
                "機材種別":             body_type,
                "座席数(ダミー)":        seats,
                "既存路線 平均最安値(円)": round(avg_price) if avg_price else None,
                f"{target_arr} 推定収益/便(円)": round(est_rev) if est_rev else None,
            })

        df_missing = pd.DataFrame(rows)
        rev_col = f"{target_arr} 推定収益/便(円)"

        col_l, col_r = st.columns([3, 2])
        with col_l:
            st.caption(f"推定収益/便 = {dep_iata}→{target_arr} 平均最安値 × 座席数(ダミー) × 搭乗率80%（参考値）")
            disp = df_missing.copy()
            disp["既存路線 平均最安値(円)"] = disp["既存路線 平均最安値(円)"].apply(
                lambda x: f"¥{x:,.0f}" if x else "—")
            disp[rev_col] = disp[rev_col].apply(lambda x: f"¥{x:,.0f}" if x else "—")
            st.dataframe(disp.sort_values(["種別", "航空会社"]),
                         use_container_width=True, hide_index=True)

        with col_r:
            rev_df = df_missing[df_missing[rev_col].notna()].copy()
            rev_df = rev_df.sort_values(rev_col, ascending=True)
            fig = px.bar(rev_df, x=rev_col, y="航空会社", color="種別",
                         orientation="h",
                         color_discrete_map={"LCC": "#F6AA00", "FSC": "#005AFF"},
                         title=f"就航時 推定収益/便（{dep_iata}→{target_arr}）")
            fig.update_layout(height=max(280, len(rev_df) * 40 + 80))
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    if not present:
        st.info("共通就航の航空会社はありません。")
    else:
        rows2 = []
        for airline in present:
            sub = df_lat[df_lat["airline"] == airline]
            carrier_type = sub["carrier_type"].iloc[0] if not sub.empty else "不明"
            routes       = [f"{dep_iata}→{a}" for a in sub["arrival_iata"].unique()]
            aircraft_used = sub["aircraft"].mode().iloc[0] if not sub["aircraft"].mode().empty else "不明"
            seats_row = aircraft_m[aircraft_m["aircraft_name"] == aircraft_used]
            seats     = int(seats_row["seats"].iloc[0]) if not seats_row.empty else None
            sub_t     = sub[sub["arrival_iata"] == target_arr]
            freq      = sub_t.groupby("flight_date").size().mean() if not sub_t.empty else 0
            est_rev   = avg_ngo_price * seats * LOAD_FACTOR if seats else None
            rows2.append({
                "航空会社":            airline,
                "種別":               carrier_type,
                "就航中の路線":        "・".join(routes),
                "使用機材":           aircraft_used,
                "現在の平均便数/日":   round(freq, 1),
                "推定収益/便(円)":     round(est_rev) if est_rev else None,
            })
        df_present = pd.DataFrame(rows2)
        disp2 = df_present.copy()
        disp2["推定収益/便(円)"] = disp2["推定収益/便(円)"].apply(lambda x: f"¥{x:,.0f}" if x else "—")
        st.dataframe(disp2.sort_values(["種別", "航空会社"]),
                     use_container_width=True, hide_index=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════
# SECTION 2: 路線優先度ランキング
# ══════════════════════════════════════════════════════════
st.markdown("## 路線優先度ランキング")
st.caption("4指標の重みを調整して、交渉戦略に合わせたスコアをシミュレーションできます。")

col1, col2, col3, col4 = st.columns(4)
with col1:
    w_price   = st.slider("💰 価格水準",      0, 100, 40, 5)
with col2:
    w_supply  = st.slider("📉 供給不足度",     0, 100, 30, 5)
with col3:
    w_nonstop = st.slider("✈️ 直行便空白",     0, 100, 20, 5)
with col4:
    w_surge   = st.slider("📈 価格高水準の恒常性", 0, 100, 10, 5)

total_w = w_price + w_supply + w_nonstop + w_surge
if total_w == 0:
    st.error("重みをすべて0にはできません。")
    st.stop()
elif total_w != 100:
    st.warning(f"⚠️ 合計 {total_w}%（100%以外は比率ベースで計算）")
else:
    st.success(f"✅ 合計 {total_w}% — スコアは正規化されています")

level_num = {"low": 1, "typical": 2, "high": 3}
agg = (summary.groupby("route_label")
       .agg(avg_level   =("price_level",   lambda x: x.map(level_num).mean()),
            high_pct    =("price_level",   lambda x: (x == "high").mean()),
            avg_flights =("total_flights", "mean"),
            min_stops   =("min_stops",     "min"))
       .reset_index())

def norm(s):
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else pd.Series([0.5] * len(s), index=s.index)

denom = total_w if total_w > 0 else 100
agg["score_price"]   = norm(agg["avg_level"])
agg["score_supply"]  = norm(1 / agg["avg_flights"].clip(lower=1))
agg["score_nonstop"] = (agg["min_stops"] > 0).astype(float)
agg["score_surge"]   = norm(agg["high_pct"])
agg["total_score"]   = (
    agg["score_price"]   * w_price   / denom +
    agg["score_supply"]  * w_supply  / denom +
    agg["score_nonstop"] * w_nonstop / denom +
    agg["score_surge"]   * w_surge   / denom
).round(4)
agg = agg.sort_values("total_score", ascending=False).reset_index(drop=True)
agg.index += 1

top = agg.iloc[0]
st.info(f"🥇 **現在の重みで最優先路線: 「{top['route_label']}」（スコア: {top['total_score']:.3f}）**  "
        f"— 価格水準 {top['avg_level']:.1f}/3・平均 {top['avg_flights']:.1f}便/日・"
        f"{'直行便なし' if top['min_stops'] > 0 else '直行便あり'}・高騰率 {top['high_pct']*100:.0f}%")

col_left, col_right = st.columns([2, 3])

with col_left:
    disp_rank = agg[["route_label", "total_score", "avg_level",
                     "avg_flights", "min_stops", "high_pct"]].copy()
    disp_rank["high_pct"]    = (disp_rank["high_pct"] * 100).round(1)
    disp_rank["avg_level"]   = disp_rank["avg_level"].round(2)
    disp_rank["avg_flights"] = disp_rank["avg_flights"].round(1)
    disp_rank.columns = ["路線", "総合スコア", "価格水準(平均)", "平均便数", "最小乗継", "高騰率(%)"]
    st.dataframe(disp_rank, use_container_width=True)

with col_right:
    breakdown = agg[["route_label"]].copy()
    breakdown["💰 価格水準"]       = (agg["score_price"]   * w_price   / denom).round(4)
    breakdown["📉 供給不足"]       = (agg["score_supply"]  * w_supply  / denom).round(4)
    breakdown["✈️ 直行便空白"]     = (agg["score_nonstop"] * w_nonstop / denom).round(4)
    breakdown["📈 価格高水準の恒常性"] = (agg["score_surge"] * w_surge / denom).round(4)
    bd_melt = breakdown.melt(id_vars="route_label", var_name="指標", value_name="スコア")
    fig_bd = px.bar(bd_melt, x="スコア", y="route_label", color="指標",
                    orientation="h", barmode="stack",
                    color_discrete_sequence=["#FF4B00", "#F6AA00", "#005AFF", "#990099"],
                    labels={"route_label": "路線"},
                    category_orders={"route_label": agg["route_label"].tolist()[::-1]})
    fig_bd.update_layout(height=280, legend_title="指標")
    st.plotly_chart(fig_bd, use_container_width=True)

# レーダーチャート
sel_route = st.selectbox("路線を選択（レーダーチャート）", agg["route_label"].tolist())
row = agg[agg["route_label"] == sel_route].iloc[0]
categories = ["価格水準", "供給不足度", "直行便空白", "価格高水準の恒常性"]
values     = [row["score_price"], row["score_supply"], row["score_nonstop"], row["score_surge"]]
fig_r = go.Figure(go.Scatterpolar(
    r=values + values[:1], theta=categories + categories[:1],
    fill="toself", fillcolor="rgba(0,90,255,0.2)",
    line_color="#005AFF", line_width=2,
))
fig_r.update_layout(
    polar=dict(radialaxis=dict(range=[0, 1])),
    height=340, title=f"{sel_route} のスコア内訳",
)
col_rc1, col_rc2 = st.columns([2, 1])
with col_rc1:
    st.plotly_chart(fig_r, use_container_width=True)
with col_rc2:
    st.markdown(f"""
**{sel_route}**

| 指標 | スコア |
|---|---|
| 💰 価格水準 | {row['score_price']:.2f} |
| 📉 供給不足度 | {row['score_supply']:.2f} |
| ✈️ 直行便空白 | {row['score_nonstop']:.2f} |
| 📈 価格高水準の恒常性 | {row['score_surge']:.2f} |
| **総合スコア** | **{row['total_score']:.3f}** |

**順位**: {agg.index[agg['route_label'] == sel_route][0]}位
""")

with st.expander("📖 重みづけの使い方"):
    st.markdown("""
| 提案先・戦略 | おすすめ設定 |
|---|---|
| FSCへ「収益性の高い路線」として提案 | 価格水準↑ 価格高水準の恒常性↑ |
| LCCへ「市場空白がある路線」として提案 | 直行便空白↑ 供給不足↑ |
| 増便交渉（既就航航空会社向け） | 供給不足↑ 価格水準↑ |
| 新規就航交渉（未就航航空会社向け） | 直行便空白↑ 価格高水準の恒常性↑ |

⚠️ 収益試算は座席数ダミー値・搭乗率80%仮定の参考値です。提案書には「HKG路線において未就航」と明記してください。
""")
