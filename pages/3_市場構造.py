"""PAGE 3 — 市場構造: 競争環境と就航余地を読む"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.loader import load_flights, load_price_history, route_summary, latest_flights, PRICE_LEVEL_COLOR
from utils.constants import IATA_COLOR

st.set_page_config(page_title="市場構造", layout="wide", page_icon="🔍")
st.title("3｜市場構造 — 競争環境と就航余地を読む")
st.caption("直行便・LCC状況・便数と価格の分布・空港間比較から、就航余地を多面的に示します。")

flights = load_flights()
ph_all  = load_price_history()
summary = route_summary(flights)
df_lat  = latest_flights(flights)
summary["flight_date_str"] = summary["flight_date"].dt.strftime("%Y-%m-%d")
summary["price_level_jp"] = summary["price_level"].map({"low": "低価格", "typical": "標準", "high": "高騰"})

dep_iata      = "HKG"
df_hkg        = flights[flights["departure_iata"] == dep_iata].copy()
summary_hkg   = summary[summary["departure_iata"] == dep_iata].copy()

AIRPORTS      = ["KIX", "NGO", "HND"]
AIRPORT_LABEL = {"KIX": "関西 (KIX)", "NGO": "中部 (NGO)", "HND": "羽田 (HND)"}
LEVEL_BG      = {"low": "#1A3E6A", "typical": "#1A3A2A", "high": "#3A2810"}
LEVEL_BADGE   = {"low": "🔵 安値", "typical": "🟢 標準", "high": "🟠 高騰"}

# ── 集計 ─────────────────────────────────────────────────
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

lcc_fsc = (
    df_lat.groupby(["route_label", "carrier_type"])
    .size().reset_index(name="便数")
)
tot_f = lcc_fsc.groupby("route_label")["便数"].sum().reset_index(name="total")
lcc_fsc = lcc_fsc.merge(tot_f, on="route_label")
lcc_fsc["割合(%)"] = (lcc_fsc["便数"] / lcc_fsc["total"] * 100).round(1)

summary_avg = (
    summary_hkg.groupby(["route_label", "arrival_iata"])
    .agg(
        avg_typical_high =("typical_high",  "mean"),
        avg_typical_low  =("typical_low",   "mean"),
        avg_lowest_price =("lowest_price",  "mean"),
        high_rate        =("price_level",   lambda x: round((x == "high").mean() * 100, 1)),
        avg_flights      =("total_flights", "mean"),
    )
    .reset_index()
)

med_f = summary["total_flights"].median()
med_p = summary["lowest_price"].median()
shortage = summary[(summary["total_flights"] < med_f) & (summary["lowest_price"] > med_p)]

# ── アラート ──────────────────────────────────────────────
ngo_dr = direct_ratio[direct_ratio["route_label"].str.contains("NGO")]
if not ngo_dr.empty:
    n = ngo_dr.iloc[0]
    st.error(
        f"🔴 **「{n['route_label']}」は直行便参入余地が最も高い** — "
        f"直行便比率 {n['直行便比率']:.0f}%（全{n['総便数']}便中{n['乗継便数']}本が乗継）"
    )
if not shortage.empty:
    top_s = shortage.sort_values("lowest_price", ascending=False).iloc[0]
    st.warning(
        f"⚠️ **供給不足シグナル: 「{top_s['route_label']}」**（{top_s['flight_date'].strftime('%m/%d')}）— "
        f"{top_s['total_flights']:.0f}便/日（中央値{med_f:.0f}）で最安値 ¥{top_s['lowest_price']:,.0f}"
    )

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["✈️ 直行便・競合状況", "💴 価格・便数の分布", "📅 搭乗日別の推移"])

# ══════════════════════════════════════════════════════════
# TAB 1: 直行便・競合状況
# ══════════════════════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### 直行便 / 乗継便の内訳（3路線比較）")
        dr = direct_ratio.sort_values("直行便比率")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=dr["route_label"], y=dr["直行便比率"],
            name="直行便", marker_color="#005AFF",
            text=dr.apply(lambda r: f"{r['直行便数']}便 ({r['直行便比率']:.0f}%)", axis=1),
            textposition="inside",
        ))
        fig_bar.add_trace(go.Bar(
            x=dr["route_label"], y=100 - dr["直行便比率"],
            base=list(dr["直行便比率"]),
            name="乗継便", marker_color="#F6AA00",
            text=dr.apply(lambda r: f"{r['乗継便数']}便", axis=1),
            textposition="inside",
        ))
        fig_bar.update_layout(
            barmode="stack", height=340, yaxis_title="割合 (%)",
            yaxis_range=[0, 115],
            legend=dict(orientation="h", y=1.05),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.markdown("#### LCC / FSC 就航構成比（3路線比較）")
        fig_lcc = px.bar(
            lcc_fsc.sort_values(["route_label", "carrier_type"]),
            x="route_label", y="割合(%)", color="carrier_type",
            barmode="stack",
            color_discrete_map={"LCC": "#F6AA00", "FSC": "#005AFF"},
            text="割合(%)",
            labels={"route_label": "路線", "carrier_type": "種別"},
        )
        fig_lcc.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
        fig_lcc.update_layout(
            height=340, legend_title="種別",
            yaxis_range=[0, 115],
        )
        st.plotly_chart(fig_lcc, use_container_width=True)

    st.markdown("#### 直行便 運航会社一覧")
    direct_al_df = (
        df_lat[df_lat["stops"] == 0]
        .groupby(["route_label", "carrier_type", "airline"])
        .size().reset_index(name="便数")
        .sort_values(["route_label", "carrier_type", "airline"])
    )
    direct_al_df["種別"] = direct_al_df["carrier_type"].map({"LCC": "🟢 LCC", "FSC": "🔵 FSC"})
    if direct_al_df.empty:
        st.info("直行便のデータがありません。")
    else:
        disp_al = direct_al_df[["route_label", "airline", "種別", "便数"]].copy()
        disp_al.columns = ["路線", "航空会社", "種別", "便数"]
        st.dataframe(disp_al, use_container_width=True, hide_index=True)

    ngo_lcc = df_lat[(df_lat["arrival_iata"] == "NGO") & (df_lat["carrier_type"] == "LCC")]
    if ngo_lcc.empty:
        st.warning("⚠️ HKG→NGO に LCC 就航なし — Peach・GBA 等への誘致余地あり")

# ══════════════════════════════════════════════════════════
# TAB 2: 価格・便数の分布
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### 便数 vs 価格 — 供給不足マップ")
    st.caption("左上（便数少・価格高）= 供給不足・就航チャンス。中央値の点線で4象限に区分。")

    fig_b3 = px.scatter(
        summary,
        x="total_flights", y="lowest_price",
        color="price_level_jp", symbol="route_label",
        hover_name="route_label",
        hover_data={"flight_date_str": True, "total_flights": True,
                    "lowest_price": ":.0f", "price_level_jp": True, "min_stops": True},
        color_discrete_map={"低価格": "#4DC4FF", "標準": "#F6AA00", "高騰": "#FF4B00"},
        category_orders={"price_level_jp": ["低価格", "標準", "高騰"]},
        labels={"total_flights": "1日の総便数", "lowest_price": "最安値（円）",
                "price_level_jp": "価格水準", "route_label": "路線",
                "flight_date_str": "搭乗日", "min_stops": "最小乗継"},
    )
    fig_b3.add_vline(x=med_f, line_dash="dash", line_color="gray",
                     annotation_text=f"中央値 {med_f:.0f}便", annotation_position="top right")
    fig_b3.add_hline(y=med_p, line_dash="dash", line_color="gray",
                     annotation_text=f"中央値 ¥{med_p:,.0f}", annotation_position="top right")
    fig_b3.add_annotation(
        x=summary["total_flights"].min() + 0.5, y=summary["lowest_price"].max() * 0.98,
        text="就航・増便チャンス",
        bgcolor="rgba(255,75,0,0.1)", bordercolor="#FF4B00",
        font=dict(color="#FF4B00", size=11), showarrow=False,
    )
    fig_b3.add_annotation(
        x=summary["total_flights"].max() * 0.85, y=summary["lowest_price"].min() * 1.05,
        text="競合多・低価格",
        bgcolor="rgba(0,90,255,0.1)", bordercolor="#005AFF",
        font=dict(color="#005AFF", size=11), showarrow=False,
    )
    fig_b3.add_annotation(
        x=summary["total_flights"].max() * 0.85, y=summary["lowest_price"].max() * 0.98,
        text="高需要・競合あり",
        bgcolor="rgba(246,170,0,0.1)", bordercolor="#F6AA00",
        font=dict(color="#B87D00", size=11), showarrow=False,
    )
    fig_b3.add_annotation(
        x=summary["total_flights"].min() + 0.5, y=summary["lowest_price"].min() * 1.05,
        text="閑散期・需要低",
        bgcolor="rgba(150,150,150,0.1)", bordercolor="gray",
        font=dict(color="gray", size=11), showarrow=False,
    )
    fig_b3.update_layout(height=420, legend=dict(title=None, tracegroupgap=4))
    st.plotly_chart(fig_b3, use_container_width=True)

    st.markdown("#### 典型価格帯 × 実勢最安値（3路線比較）")
    st.caption("帯 = 標準価格レンジ（typical_low〜typical_high）。◆ = 実勢平均最安値。")

    fig_band = go.Figure()
    fig_band.add_trace(go.Bar(
        x=list(summary_avg["route_label"]),
        y=list(summary_avg["avg_typical_low"]),
        name="", marker_color="rgba(0,0,0,0)", showlegend=False, hoverinfo="skip",
    ))
    fig_band.add_trace(go.Bar(
        x=list(summary_avg["route_label"]),
        y=list(summary_avg["avg_typical_high"] - summary_avg["avg_typical_low"]),
        base=list(summary_avg["avg_typical_low"]),
        name="典型価格帯",
        marker_color="rgba(100,149,237,0.45)",
        marker_line=dict(color="steelblue", width=2),
    ))
    for _, row in summary_avg.iterrows():
        fig_band.add_annotation(
            x=row["route_label"], y=row["avg_typical_high"],
            text=f"上限 ¥{row['avg_typical_high']:,.0f}",
            showarrow=False, font=dict(size=10, color="steelblue"),
            yanchor="bottom", yshift=4,
        )
    fig_band.add_trace(go.Scatter(
        x=list(summary_avg["route_label"]),
        y=list(summary_avg["avg_lowest_price"]),
        mode="markers+text", name="実勢平均最安値",
        marker=dict(size=16, color="#FF4B00", symbol="diamond",
                    line=dict(color="white", width=2)),
        text=list(summary_avg["avg_lowest_price"].apply(lambda x: f"¥{x:,.0f}")),
        textposition="bottom center", textfont=dict(color="#FF4B00", size=11),
    ))
    _yband_min = summary_avg["avg_typical_low"].min()
    _yband_max = max(summary_avg["avg_typical_high"].max(), summary_avg["avg_lowest_price"].max())
    fig_band.update_layout(
        barmode="stack", height=320, yaxis_title="価格 ¥",
        yaxis=dict(range=[_yband_min * 0.85, _yband_max * 1.15]),
        legend=dict(orientation="h", y=1.02),
    )
    st.plotly_chart(fig_band, use_container_width=True)

    with st.expander("詳細データ — 路線 × 搭乗日"):
        disp = summary[["route_label", "flight_date_str", "total_flights",
                        "lowest_price", "price_level", "min_stops"]].copy()
        disp.columns = ["路線", "搭乗日", "総便数", "最安値（円）", "価格水準", "最小乗継"]
        disp = disp.sort_values(["価格水準", "総便数"], ascending=[False, True])
        st.dataframe(disp, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
# TAB 3: 搭乗日別の推移
# ══════════════════════════════════════════════════════════
with tab3:
    # 月フィルタ
    _months_tab3 = sorted(summary_hkg["flight_date"].dt.to_period("M").astype(str).unique())
    _sel_month_tab3 = st.selectbox(
        "搭乗月を選択", _months_tab3,
        index=len(_months_tab3) - 1, key="tab3_month",
        help="月を絞り込むと搭乗日ごとの棒グラフが見やすくなります",
    )
    _summary_tab3 = summary_hkg[
        summary_hkg["flight_date"].dt.to_period("M").astype(str) == _sel_month_tab3
    ].copy()

    col_p, col_f = st.columns(2)

    with col_p:
        st.markdown("#### 搭乗日別 最安値（3路線比較）")
        fig1 = px.bar(
            _summary_tab3.assign(fd=_summary_tab3["flight_date"].dt.strftime("%Y/%m/%d")),
            x="fd", y="lowest_price", color="arrival_iata", barmode="group",
            color_discrete_map=IATA_COLOR,
            labels={"fd": "搭乗日", "lowest_price": "最安値(円)", "arrival_iata": "到着空港"},
        )
        fig1.update_layout(height=340, legend_title="空港")
        st.plotly_chart(fig1, use_container_width=True)

    with col_f:
        st.markdown("#### 搭乗日別 便数（3路線比較）")
        fig2 = px.bar(
            _summary_tab3.assign(fd=_summary_tab3["flight_date"].dt.strftime("%Y/%m/%d")),
            x="fd", y="total_flights", color="arrival_iata", barmode="group",
            color_discrete_map=IATA_COLOR,
            labels={"fd": "搭乗日", "total_flights": "総便数", "arrival_iata": "到着空港"},
        )
        fig2.update_layout(height=340, legend_title="空港")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### 搭乗日 × 空港 価格マトリクス")
    st.caption("各セルは最安値（円）と価格水準。NGO列に高値が多いほど需要が強い。")

    search_dates = sorted(df_hkg["search_date"].dt.strftime("%Y-%m-%d").unique())
    if search_dates:
        col_sd, col_cb = st.columns([3, 1])
        with col_sd:
            sel_search = st.selectbox(
                "観測日（検索日）を選択", search_dates,
                index=len(search_dates) - 1, key="mkt_search_date",
            )
        with col_cb:
            show_band = st.checkbox("典型価格帯を表示", value=True, key="mkt_show_band")

        df_mx = df_hkg[df_hkg["search_date"].dt.strftime("%Y-%m-%d") == sel_search].copy()
        if df_mx.empty:
            st.warning("選択条件に該当するデータがありません。")
        else:
            mx_summary = (
                df_mx.groupby(["flight_date", "arrival_iata"])
                .agg(
                    lowest_price =("route_lowest_price",    "min"),
                    typical_low  =("route_typical_low",     "first"),
                    typical_high =("route_typical_high",    "first"),
                    price_level  =("route_price_level",     "first"),
                    flight_count =("total_flights_on_day",  "first"),
                )
                .reset_index()
            )
            mx_summary["flight_date_str"] = mx_summary["flight_date"].dt.strftime("%Y-%m-%d")

            dates    = sorted(mx_summary["flight_date_str"].unique())
            airports = [a for a in AIRPORTS if a in mx_summary["arrival_iata"].unique()]
            header_vals = ["<b>搭乗日</b>"] + [f"<b>{AIRPORT_LABEL[a]}</b>" for a in airports]
            col_vals    = [dates]
            col_colors  = [["#162E52"] * len(dates)]

            for airport in airports:
                vals, colors = [], []
                for d in dates:
                    row = mx_summary[
                        (mx_summary["flight_date_str"] == d) &
                        (mx_summary["arrival_iata"] == airport)
                    ]
                    if row.empty:
                        vals.append("—"); colors.append("#0F2240")
                    else:
                        lp    = row["lowest_price"].values[0]
                        tl    = row["typical_low"].values[0]
                        th    = row["typical_high"].values[0]
                        lv    = (row["price_level"].values[0] or "typical").lower()
                        fc    = int(row["flight_count"].values[0]) if pd.notna(row["flight_count"].values[0]) else 0
                        badge = LEVEL_BADGE.get(lv, "🟢 標準")
                        if show_band and pd.notna(tl) and pd.notna(th):
                            cell = (f"¥{int(lp):,}  {badge}<br>"
                                    f"<span style='font-size:11px'>帯: ¥{int(tl):,}〜¥{int(th):,}</span><br>"
                                    f"<span style='font-size:11px'>{fc}便</span>")
                        else:
                            cell = f"¥{int(lp):,}  {badge}<br><span style='font-size:11px'>{fc}便</span>"
                        vals.append(cell)
                        colors.append(LEVEL_BG.get(lv, "#1A3A2A"))
                col_vals.append(vals); col_colors.append(colors)

            row_h = 62
            fig_mx = go.Figure(data=[go.Table(
                columnwidth=[120] + [200] * len(airports),
                header=dict(
                    values=header_vals, fill_color="#0F2240",
                    font=dict(color="#D4E4F5", size=13), align="center",
                    height=38, line=dict(color="#1E3A64", width=1),
                ),
                cells=dict(
                    values=col_vals, fill_color=col_colors,
                    font=dict(color="#D4E4F5", size=12), align="center",
                    height=row_h, line=dict(color="#1E3A64", width=1),
                ),
            )])
            fig_mx.update_layout(
                margin=dict(l=0, r=0, t=4, b=4),
                height=38 + row_h * len(dates) + 16,
                paper_bgcolor="#0B1829",
            )
            st.plotly_chart(fig_mx, use_container_width=True)

            # 路線間 価格差（NGO比較）
            _pivot_diff = mx_summary.pivot_table(
                index="flight_date_str", columns="arrival_iata", values="lowest_price"
            ).reindex(dates)
            _diff_rows = []
            for _d in dates:
                if _d not in _pivot_diff.index:
                    continue
                _r = _pivot_diff.loc[_d]
                _ngo = _r.get("NGO"); _kix = _r.get("KIX"); _hnd = _r.get("HND")
                if pd.notna(_ngo) and pd.notna(_kix):
                    _diff_rows.append({"搭乗日": _d, "比較": "NGO vs KIX",
                                       "NGO": f"¥{int(_ngo):,}", "KIX": f"¥{int(_kix):,}",
                                       "差額": f"¥{int(_ngo - _kix):+,}"})
                if pd.notna(_ngo) and pd.notna(_hnd):
                    _diff_rows.append({"搭乗日": _d, "比較": "NGO vs HND",
                                       "NGO": f"¥{int(_ngo):,}", "HND": f"¥{int(_hnd):,}",
                                       "差額": f"¥{int(_ngo - _hnd):+,}"})
            if _diff_rows:
                with st.expander("路線間 価格差（NGO比較）"):
                    st.caption("差額がプラス = NGOの方が高い = NGO旅客が高い運賃を負担している")
                    st.dataframe(pd.DataFrame(_diff_rows), use_container_width=True, hide_index=True)
