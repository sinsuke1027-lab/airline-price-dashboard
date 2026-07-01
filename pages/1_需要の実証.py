"""PAGE 1 — 需要の実証: 「この路線に需要がある」を証明する"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from utils.loader import (load_flights, load_price_history,
                          route_summary, PRICE_LEVEL_LABEL)
from utils.constants import ROUTE_COLOR

st.set_page_config(page_title="需要の実証", layout="wide", page_icon="📈")
st.title("1｜需要の実証 — 「この路線に需要がある」を証明する")
st.caption("価格カレンダー・航空会社別運賃・ブッキングカーブ・収益概算の4視点で、路線誘致の需要根拠を組み立てます。")

flights = load_flights()
ph      = load_price_history()
summary = route_summary(flights)
summary["flight_date_str"] = summary["flight_date"].dt.strftime("%m/%d")
ph_hkg  = ph[ph["departure_iata"] == "HKG"].copy()

# サイドバー: 観測時点セレクター（全タブ共通）
_SNAP_LABELS = ["14日前（直前）", "30日前（1ヶ月前）", "60日前（2ヶ月前）", "90日前（3ヶ月前）"]
_SNAP_VALS   = [14, 30, 60, 90]
snap_idx = st.sidebar.selectbox(
    "カレンダー: 観測時点",
    range(len(_SNAP_LABELS)),
    format_func=lambda i: _SNAP_LABELS[i],
    index=2,
    help="全搭乗月を同じ「何日前の価格」で比較します。60日前なら2ヶ月前に検索したときの水準。",
)
snap_db = _SNAP_VALS[snap_idx]
_TOL = 20

ph_snap = ph_hkg[
    ph_hkg["days_before_dep"].between(snap_db - _TOL, snap_db + _TOL)
].copy()

# ── アラート ───────────────────────────────────────────────
high = summary[summary["price_level"] == "high"].sort_values("lowest_price", ascending=False)
if not high.empty:
    top = high.iloc[0]
    st.error(
        f"🔴 **最も価格が高騰: 「{top['route_label']}」（{top['flight_date'].strftime('%m/%d')}）— ¥{top['lowest_price']:,.0f}**  "
        f"典型価格帯 ¥{top['typical_low']:,.0f}〜¥{top['typical_high']:,.0f} を上回る水準。増便・新規就航で収益が見込めます。"
    )

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📅 価格の実態", "✈️ 航空会社・運賃詳細", "💰 収益概算"])

# ══════════════════════════════════════════════════════════
# TAB 1: 価格の実態
# ══════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 価格カレンダー — 同じタイミングで見た月別価格")
    st.caption(
        "「出発N日前時点の価格」を統一して全搭乗月を比較します。"
        "同じ条件（何日前か）で並べることで、季節による需要の強弱が見えやすくなります。"
        "**赤い月 = その時点で既に価格が高い = 早期から需要が旺盛**。"
    )

    if ph_snap.empty:
        st.info(
            f"「{_SNAP_LABELS[snap_idx]}」のデータが見つかりません。"
            " combined モードを選択するか、別の観測時点を試してください。"
            " 以下に最新検索日ベースの日次カレンダーを表示します。"
        )
        _lv = {"low": 1, "typical": 2, "high": 3}
        summary["_lv_num"] = summary["price_level"].map(_lv).fillna(2)
        summary["_cell"]   = summary.apply(
            lambda r: f"¥{r['lowest_price']:,.0f}<br>{PRICE_LEVEL_LABEL.get(r['price_level'], '-')}",
            axis=1,
        )
        _routes_fb = sorted(summary["route_label"].unique())
        _dates_fb  = sorted(summary["flight_date_str"].unique())
        _z_fb, _txt_fb = [], []
        for _r in _routes_fb:
            _zr, _tr = [], []
            for _d in _dates_fb:
                _row = summary[(summary["route_label"] == _r) & (summary["flight_date_str"] == _d)]
                _zr.append(_row.iloc[0]["_lv_num"] if not _row.empty else None)
                _tr.append(_row.iloc[0]["_cell"]   if not _row.empty else "")
            _z_fb.append(_zr); _txt_fb.append(_tr)
        fig_heat = go.Figure(go.Heatmap(
            z=_z_fb, x=_dates_fb, y=_routes_fb, text=_txt_fb, texttemplate="%{text}",
            colorscale=[[0, "#4DC4FF"], [0.5, "#F6AA00"], [1.0, "#FF4B00"]],
            zmin=1, zmax=3, showscale=False,
            hovertemplate="路線: %{y}<br>日付: %{x}<br>%{text}<extra></extra>",
        ))
        fig_heat.update_layout(
            height=300 + len(_routes_fb) * 70,
            xaxis_title="搭乗日", yaxis_title="路線",
            margin=dict(l=130, r=20, t=20, b=40),
        )
    else:
        ph_snap["flight_month"] = ph_snap["flight_date"].dt.to_period("M").astype(str)
        heat = (
            ph_snap.groupby(["route_label", "flight_month"])
            .agg(
                avg_price=("price_jpy",   "mean"),
                high_rate=("price_level", lambda x: round((x == "high").mean() * 100, 1)),
                n_obs    =("price_jpy",   "count"),
            )
            .reset_index()
        )
        _routes_h = sorted(heat["route_label"].unique())
        _months_h = sorted(heat["flight_month"].unique())

        _z, _txt = [], []
        for _r in _routes_h:
            _zr, _tr = [], []
            for _m in _months_h:
                _row = heat[(heat["route_label"] == _r) & (heat["flight_month"] == _m)]
                if not _row.empty:
                    _p  = _row.iloc[0]["avg_price"]
                    _hr = _row.iloc[0]["high_rate"]
                    _zr.append(_hr)
                    _tr.append(f"¥{_p:,.0f}<br>高騰{_hr:.0f}%")
                else:
                    _zr.append(None)
                    _tr.append("─")
            _z.append(_zr); _txt.append(_tr)

        fig_heat = go.Figure(go.Heatmap(
            z=_z, x=_months_h, y=_routes_h, text=_txt, texttemplate="%{text}",
            colorscale=[[0, "#4DC4FF"], [0.25, "#F6AA00"], [0.55, "#FF4B00"], [1.0, "#990099"]],
            zmin=0, zmax=100, showscale=True,
            colorbar=dict(title="高騰率(%)", thickness=12, len=0.75,
                          tickvals=[0, 25, 50, 75, 100],
                          ticktext=["0% 低", "25%", "50%", "75%", "100% 全高騰"]),
            hovertemplate="路線: %{y}<br>搭乗月: %{x}<br>%{text}<extra></extra>",
        ))

        _PEAK_MAP = {
            "2025-12": "年末年始", "2026-01": "年始",
            "2026-05": "GW", "2026-07": "夏休み", "2026-08": "お盆",
        }
        for _pm, _lbl in _PEAK_MAP.items():
            if _pm in _months_h:
                fig_heat.add_annotation(
                    x=_pm, y=len(_routes_h) - 0.5,
                    text=f"<b>▲{_lbl}</b>",
                    showarrow=False,
                    font=dict(size=9, color="#FF4B00"),
                    yanchor="bottom",
                )

        fig_heat.update_layout(
            height=300 + len(_routes_h) * 100,
            xaxis_title=f"搭乗月　（観測時点: 出発 {snap_db} 日前前後の価格）",
            yaxis_title="路線",
            margin=dict(l=130, r=110, t=50, b=40),
        )

    st.plotly_chart(fig_heat, use_container_width=True)
    st.caption(
        f"色 = その月の搭乗便を「出発{snap_db}日前」前後で観測したときの**価格高騰率**"
        "（0%=全て標準・低価格 / 100%=全て高騰）。"
        "繁忙期目安: 年末年始(12〜1月) ／ GW(5月) ／ 夏休み・お盆(7〜8月)  "
        "⚠️ 価格高騰は需要の代理指標。「便数が少ない月の高騰」がより信頼できるシグナル（→ 市場構造ページ）。"
    )

    # ─── 価格水準の月別内訳 ───────────────────────────────
    st.markdown("### 月別 価格水準の内訳")
    st.caption(
        f"観測時点（出発{snap_db}日前±{_TOL}日）に絞った価格データを、"
        "搭乗月ごとに低価格／標準／高騰の割合で示します。"
        "カレンダーの「高騰率」が高い月の内訳確認に使えます。"
    )

    if not ph_snap.empty:
        if "flight_month" not in ph_snap.columns:
            ph_snap["flight_month"] = ph_snap["flight_date"].dt.to_period("M").astype(str)
        _lv_dist = (
            ph_snap.groupby(["route_label", "flight_month", "price_level"])
            .size().reset_index(name="件数")
        )
        _lv_tot = (
            _lv_dist.groupby(["route_label", "flight_month"])["件数"]
            .sum().reset_index(name="合計")
        )
        _lv_dist = _lv_dist.merge(_lv_tot, on=["route_label", "flight_month"])
        _lv_dist["割合(%)"] = (_lv_dist["件数"] / _lv_dist["合計"] * 100).round(1)
        _lv_dist["price_level_jp"] = _lv_dist["price_level"].map(
            {"low": "低価格", "typical": "標準", "high": "高騰"}
        )

        fig_dist = px.bar(
            _lv_dist,
            x="flight_month", y="割合(%)", color="price_level_jp",
            facet_col="route_label",
            barmode="stack",
            color_discrete_map={"低価格": "#4DC4FF", "標準": "#F6AA00", "高騰": "#FF4B00"},
            category_orders={"price_level_jp": ["低価格", "標準", "高騰"]},
            labels={"flight_month": "", "割合(%)": "割合 (%)", "price_level_jp": "価格水準"},
        )
        fig_dist.for_each_annotation(lambda a: a.update(
            text=a.text.split("=")[-1],
            font=dict(size=13, color="#333"),
        ))
        fig_dist.update_xaxes(tickangle=45, tickfont=dict(size=10))
        fig_dist.update_yaxes(range=[0, 101], ticksuffix="%")
        fig_dist.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(
                title="価格水準",
                orientation="h",
                y=-0.18, x=0.5, xanchor="center",
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        fig_dist.update_traces(marker_line_width=0)
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.info("観測時点フィルター後のデータがありません。")

    st.markdown("---")

    # ─── expanders ───────────────────────────────────────
    search_dates = sorted(ph_hkg["search_date"].dt.strftime("%Y-%m-%d").unique())
    if len(search_dates) >= 2:
        with st.expander(f"📅 観測日をまたいだ価格変化（{search_dates[0]} → {search_dates[-1]}）"):
            st.caption("同じ搭乗日を複数時点で観測し、価格が上昇傾向にあるかを確認します。")
            first_sd, last_sd = search_dates[0], search_dates[-1]
            df_first = ph_hkg[ph_hkg["search_date"].dt.strftime("%Y-%m-%d") == first_sd]
            df_last  = ph_hkg[ph_hkg["search_date"].dt.strftime("%Y-%m-%d") == last_sd]

            def latest_price(d):
                return (d.groupby(["route_label", "flight_date"])
                        .apply(lambda g: g.sort_values("price_date").iloc[-1]["price_jpy"])
                        .reset_index(name="price"))

            p_first  = latest_price(df_first).rename(columns={"price": "price_first"})
            p_last   = latest_price(df_last).rename(columns={"price": "price_last"})
            merged   = p_first.merge(p_last, on=["route_label", "flight_date"], how="inner")
            merged["変化（円）"] = (merged["price_last"] - merged["price_first"]).round(0)
            merged["変化率（%）"] = ((merged["price_last"] - merged["price_first"])
                                   / merged["price_first"] * 100).round(1)
            merged["flight_date_str"] = merged["flight_date"].dt.strftime("%m/%d")
            merged["判定"] = merged["変化率（%）"].apply(
                lambda x: "🔴 上昇傾向" if x > 10 else "🟢 下落傾向" if x < -10 else "🟡 横ばい")
            disp = merged[["route_label", "flight_date_str", "price_first",
                            "price_last", "変化（円）", "変化率（%）", "判定"]].copy()
            disp.columns = ["路線", "搭乗日", f"価格({first_sd})", f"価格({last_sd})",
                            "変化（円）", "変化率（%）", "判定"]
            st.dataframe(disp.sort_values("変化率（%）", ascending=False),
                         use_container_width=True, hide_index=True)
            st.caption("⚠️ 観測期間が短いため価格変化の方向性は参考値です。データ蓄積で精度が向上します。")

    with st.expander("📖 読み解き方・提案書への活用"):
        st.markdown("""
**⚠️ 価格高騰の解釈に注意**

価格が高い理由は複数考えられます:
- **需要過多（座席不足）**: 旅客が多く残席が少ない → 就航・増便の根拠になる
- **運賃戦略**: 航空会社が意図的に高い運賃クラスのみ開放している → 需要の証拠にはならない
- **競合少・競争圧力なし**: 選択肢がないため高値維持

**「便数が少ない かつ 価格が高い」= より強い需要シグナル**
→ 便数が少ないのに価格が高い = 供給不足の可能性が高い。「市場構造」ページの散布図の左上がこれに該当します。

**価格カレンダーの「赤の多さ」= 需要の継続性**
→ 複数の搭乗日にわたって高騰 = 構造的な需要過多。「観測期間の○%が高価格水準」として提案書に使えますが、便数状況も合わせて記載してください。

**ブッキングカーブが右上がり = 早期需要の証拠**
→ 出発日に近づくほど価格が上がっている = 早期から席が埋まっているサイン。
ただし、これも残席管理（Revenue Management）の影響で起こる場合があります。

⚠️ データはSerpAPI経由のGoogle Flights推定値（参考値）です。実際の販売履歴・搭乗率ではありません。
""")

    with st.expander("数値テーブル（路線 × 搭乗日）— 需要シグナル強度付き"):
        med_f_tbl = summary["total_flights"].median()
        disp2 = summary[["route_label", "flight_date_str", "lowest_price",
                         "price_level", "typical_low", "typical_high",
                         "total_flights", "min_stops"]].copy()

        def _sig_label(row):
            if row["price_level"] == "high" and row["total_flights"] < med_f_tbl:
                return "🔴 強（便数少＋高騰）"
            elif row["price_level"] == "high":
                return "🟡 中（高騰のみ）"
            elif row["price_level"] == "typical":
                return "⚪ 標準"
            else:
                return "🟢 低価格"

        disp2["需要シグナル"] = disp2.apply(_sig_label, axis=1)
        disp2.columns = ["路線", "搭乗日", "最安値（円）", "価格水準", "典型下限", "典型上限",
                         "総便数", "最小乗継", "需要シグナル"]
        st.caption("🔴 強 = 便数も少ない（供給不足の可能性高）　🟡 中 = 高騰しているが便数は多い（運賃戦略の影響も考慮）")
        st.dataframe(disp2.sort_values(["路線", "搭乗日"]), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════
# TAB 2: 航空会社・運賃詳細
# ══════════════════════════════════════════════════════════
with tab2:
    # ─── 航空会社別 価格 × 便数 ──────────────────────────
    st.markdown("### 航空会社別 価格・便数")
    st.caption(
        f"観測時点: 出発 **{snap_db}日前** ±{_TOL}日（カレンダーと同一条件）。"
        "各路線につき左列=運賃（緑→赤）/ 右列=便数（薄青→濃青）。行順は価格の安い順。"
    )

    _fl_al = flights[flights["departure_iata"] == "HKG"].copy()
    if "search_date" in _fl_al.columns:
        _fl_al["_days_ahead"] = (
            pd.to_datetime(_fl_al["flight_date"]) - pd.to_datetime(_fl_al["search_date"])
        ).dt.days
        _fl_al = _fl_al[_fl_al["_days_ahead"].between(snap_db - _TOL, snap_db + _TOL)]
    _fl_al["flight_month"] = _fl_al["flight_date"].dt.to_period("M").astype(str)

    _al_stats = (
        _fl_al.groupby(["route_label", "flight_month", "airline", "carrier_type"])
        .agg(avg_price=("price_jpy", "mean"),
             min_price=("price_jpy", "min"),
             max_price=("price_jpy", "max"))
        .reset_index()
    )

    _all_months = sorted(_al_stats["flight_month"].unique())
    _sel_month  = st.selectbox(
        "搭乗月を選択", _all_months,
        index=len(_all_months) - 1, key="al_month_pivot",
    )

    _sub_m = _al_stats[_al_stats["flight_month"] == _sel_month].copy()

    if _sub_m.empty:
        st.info("選択月のデータなし")
    else:
        _pivot_p = (
            _sub_m.pivot_table(index="airline", columns="route_label",
                               values="avg_price", aggfunc="mean").round(0)
        )
        _pivot_p    = _pivot_p.loc[_pivot_p.mean(axis=1).sort_values().index]
        _routes_all = list(_pivot_p.columns)
        _airlines_p = list(_pivot_p.index)
        _ct_map     = _sub_m.groupby("airline")["carrier_type"].first().to_dict()
        _y_labels   = [f"{a}  [LCC]" if _ct_map.get(a) == "LCC" else a for a in _airlines_p]
        _n_routes   = len(_routes_all)

        _p_dict = {}
        for _, _row in _sub_m.iterrows():
            _p_dict[(_row["airline"], _row["route_label"])] = (
                _row["avg_price"], _row["min_price"], _row["max_price"]
            )
        _cnt_fl = _fl_al[_fl_al["flight_month"] == _sel_month]
        _c_dict = (
            _cnt_fl.groupby(["airline", "route_label"]).size()
            .reset_index(name="n").set_index(["airline", "route_label"])["n"].to_dict()
        )

        _pv_all = [float(v[0]) for v in _p_dict.values() if not pd.isna(v[0])]
        _p_min, _p_max = (min(_pv_all), max(_pv_all)) if _pv_all else (0, 1)
        _p_rng = _p_max - _p_min or 1
        def _fc_p(v):
            n = (v - _p_min) / _p_rng
            return "white" if (n < 0.22 or n > 0.78) else "black"

        _cv_all = [v for v in _c_dict.values() if v > 0]
        _c_min, _c_max = (min(_cv_all), max(_cv_all)) if _cv_all else (0, 1)
        _c_rng = _c_max - _c_min or 1
        def _fc_c(v):
            return "white" if (v - _c_min) / _c_rng > 0.70 else "black"

        _col_widths = [w for _ in _routes_all for w in [2, 1]]
        _subtitles  = [t for _r in _routes_all
                       for t in [_r.split("→")[-1] if "→" in _r else _r, " "]]
        _fig = make_subplots(
            rows=1, cols=_n_routes * 2,
            shared_yaxes=True,
            column_widths=_col_widths,
            subplot_titles=_subtitles,
            horizontal_spacing=0.01,
        )

        _annots = []
        for _ri, _r in enumerate(_routes_all):
            _col_p = _ri * 2 + 1
            _col_c = _ri * 2 + 2
            _xref_p = "x" if _col_p == 1 else f"x{_col_p}"
            _xref_c = f"x{_col_c}"

            _zp = [[float(_p_dict[(_a, _r)][0])] if (_a, _r) in _p_dict and not pd.isna(_p_dict[(_a, _r)][0])
                   else [None] for _a in _airlines_p]
            _cdp = [[[int(_p_dict[(_a, _r)][1]), int(_p_dict[(_a, _r)][2])]]
                    if (_a, _r) in _p_dict and not pd.isna(_p_dict[(_a, _r)][0])
                    else [[0, 0]] for _a in _airlines_p]
            _zc = [[int(_c_dict[(_a, _r)])] if (_a, _r) in _c_dict and _c_dict[(_a, _r)] > 0
                   else [None] for _a in _airlines_p]

            _fig.add_trace(go.Heatmap(
                z=_zp, x=["価格"], y=_y_labels,
                customdata=_cdp,
                colorscale=[[0,"#005AFF"],[0.35,"#4DC4FF"],[0.55,"#F9F9F9"],[1.0,"#FF4B00"]],
                zmin=_p_min, zmax=_p_max,
                showscale=(_ri == 0),
                colorbar=dict(title="円", thickness=10, len=0.45, x=1.02, y=0.9, yanchor="top"),
                hovertemplate=(
                    f"<b>%{{y}}</b> / {_r}<br>"
                    "平均: ¥%{z:,.0f}<br>"
                    "最安: ¥%{customdata[0]:,}<br>"
                    "最高: ¥%{customdata[1]:,}<extra></extra>"
                ),
            ), row=1, col=_col_p)

            _fig.add_trace(go.Heatmap(
                z=_zc, x=["便数"], y=_y_labels,
                colorscale=[[0,"#E8F4FD"],[0.5,"#4DC4FF"],[1.0,"#005AFF"]],
                zmin=_c_min, zmax=_c_max,
                showscale=(_ri == 0),
                colorbar=dict(title="便", thickness=10, len=0.45, x=1.02, y=0.42, yanchor="top"),
                hovertemplate=f"<b>%{{y}}</b> / {_r}<br>%{{z}}便<extra></extra>",
            ), row=1, col=_col_c)

            for _i, _yl in enumerate(_y_labels):
                _vp = _zp[_i][0]
                _vc = _zc[_i][0]
                if _vp is not None:
                    _mn, _mx = _cdp[_i][0]
                    _annots.append(dict(
                        x="価格", y=_yl,
                        text=f"<b>¥{_vp:,.0f}</b><br>¥{_mn:,}〜¥{_mx:,}",
                        showarrow=False,
                        font=dict(size=9, color=_fc_p(_vp)),
                        xref=_xref_p, yref="y", align="center",
                    ))
                else:
                    _annots.append(dict(x="価格", y=_yl, text="―", showarrow=False,
                                        font=dict(size=10, color="#bbb"), xref=_xref_p, yref="y"))
                if _vc is not None:
                    _annots.append(dict(
                        x="便数", y=_yl, text=f"{_vc}便",
                        showarrow=False,
                        font=dict(size=10, color=_fc_c(_vc)),
                        xref=_xref_c, yref="y", align="center",
                    ))
                else:
                    _annots.append(dict(x="便数", y=_yl, text="―", showarrow=False,
                                        font=dict(size=10, color="#bbb"), xref=_xref_c, yref="y"))

        _fig.update_layout(
            height=max(420, len(_airlines_p) * 55),
            margin=dict(l=10, r=90, t=50, b=40),
            annotations=_fig.layout.annotations + tuple(_annots),
        )
        st.plotly_chart(_fig, use_container_width=True)
        st.caption("[LCC] = 低コスト航空　| ― = データなし")

    st.markdown("---")

    # ─── ブッキングカーブ ──────────────────────────────────
    st.markdown("### ブッキングカーブ — 出発日に近づくにつれ価格はどう変わるか")
    st.caption("右側（出発日に近い）ほど価格が上がっている = 早期から席が埋まっている = 需要が強い証拠")

    routes_avail = sorted(ph_hkg["route_label"].unique())
    fd_options   = sorted(ph_hkg["flight_date"].dt.strftime("%Y-%m-%d").unique())

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        sel_routes = st.multiselect("路線を選択（複数選択で比較）", routes_avail,
                                    default=routes_avail)
    with col_f2:
        default_fd = "2026-06-29" if "2026-06-29" in fd_options else fd_options[0]
        sel_fd = st.selectbox("搭乗日を選択", fd_options,
                              index=fd_options.index(default_fd))

    if sel_routes:
        curve_data = ph_hkg[
            (ph_hkg["route_label"].isin(sel_routes)) &
            (ph_hkg["flight_date"].dt.strftime("%Y-%m-%d") == sel_fd) &
            ph_hkg["days_before_dep"].notna()
        ].copy()
        curve_data = curve_data[curve_data["days_before_dep"] >= 0].sort_values(
            "days_before_dep", ascending=False)

        if curve_data.empty:
            st.info("選択した搭乗日のデータがありません。別の搭乗日を選択してください。")
        else:
            fig_curve = px.line(
                curve_data, x="days_before_dep", y="price_jpy", color="route_label",
                markers=True,
                color_discrete_map={k: v for k, v in ROUTE_COLOR.items()
                                    if k in sel_routes},
                labels={"days_before_dep": "出発何日前（右ほど出発日に近い）",
                        "price_jpy": "最安値（円）", "route_label": "路線"},
                title=f"{sel_fd} 便 — ブッキングカーブ",
            )
            fig_curve.update_xaxes(autorange="reversed")
            fig_curve.update_layout(height=380, legend_title="路線")
            st.plotly_chart(fig_curve, use_container_width=True)

            slope_rows = []
            for r in sel_routes:
                sub = curve_data[curve_data["route_label"] == r]
                p_far  = sub[sub["days_before_dep"] >= 55]["price_jpy"].mean()
                p_near = sub[sub["days_before_dep"] <= 14]["price_jpy"].mean()
                if pd.notna(p_far) and pd.notna(p_near) and p_far > 0:
                    slope_pct = (p_near - p_far) / p_far * 100
                    slope_rows.append({
                        "路線": r,
                        "出発60日前の価格（円）": round(p_far),
                        "出発14日前の価格（円）": round(p_near),
                        "価格上昇率（%）": round(slope_pct, 1),
                        "判定": ("🔴 需要旺盛（早期から売れている）" if slope_pct > 10
                                 else "🟡 標準的な推移" if slope_pct >= 0
                                 else "🟢 出発直前に安くなる傾向"),
                    })
            if slope_rows:
                st.markdown("#### 価格上昇率（出発60日前 vs 14日前）")
                st.dataframe(pd.DataFrame(slope_rows), use_container_width=True, hide_index=True)

        available_searches = sorted(
            ph_hkg[ph_hkg["flight_date"].dt.strftime("%Y-%m-%d") == sel_fd]
            ["search_date"].dt.strftime("%Y-%m-%d").unique()
        )
        if len(available_searches) > 1:
            st.info(f"この搭乗日は {len(available_searches)} 回観測されています: "
                    + " / ".join(available_searches))


# ══════════════════════════════════════════════════════════
# TAB 3: 収益概算
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 収益概算 — 航空会社 × 路線マトリクス")
    st.caption(
        "月・座席数・予約比率係数を設定すると、航空会社 × 路線の推定収益を一覧表示します。"
        "収益 = Σ（便数 × 座席数 × 各時期の係数 × 各時期の平均価格）　係数は自動正規化（合計 = 1.0）。"
    )

    _REV_PERIODS  = [90, 60, 30, 14]
    _REV_DEFAULTS = [0.15, 0.25, 0.35, 0.25]

    _set_col, _slid_col = st.columns([1, 2])

    with _set_col:
        _rev_month_opts = sorted(ph_hkg["flight_date"].dt.to_period("M").astype(str).unique())
        _rev_month = st.selectbox(
            "搭乗月", _rev_month_opts,
            index=max(len(_rev_month_opts) - 1, 0),
            key="rev_month",
        )
        _rev_seats = st.slider("想定座席数 / 便", 100, 350, 180, step=10, key="rev_seats")

    with _slid_col:
        st.markdown("**各時期の予約比率**（スライダー比率で自動正規化 → 合計 = 1.0）")
        _raw_coefs = []
        _slid_cols = st.columns(len(_REV_PERIODS))
        for _sc, _d, _dv in zip(_slid_cols, _REV_PERIODS, _REV_DEFAULTS):
            _raw_coefs.append(
                _sc.slider(f"{_d}日前", 0.05, 0.60, _dv, step=0.05, key=f"rev_c_{_d}")
            )
        _coef_sum = sum(_raw_coefs) or 1.0
        _coefs    = [c / _coef_sum for c in _raw_coefs]
        st.caption(
            "正規化後: "
            + "　".join([f"**{d}日前** {c:.0%}" for d, c in zip(_REV_PERIODS, _coefs)])
        )

    _fl_all = flights[flights["departure_iata"] == "HKG"].copy()
    if "search_date" in _fl_all.columns:
        _fl_all["_da"] = (
            pd.to_datetime(_fl_all["flight_date"]) - pd.to_datetime(_fl_all["search_date"])
        ).dt.days
    _fl_all["_fm"] = _fl_all["flight_date"].dt.to_period("M").astype(str)
    _fl_m = _fl_all[_fl_all["_fm"] == _rev_month]

    _price_at = {}
    for _d in _REV_PERIODS:
        _ph_d = _fl_m[_fl_m["_da"].between(_d - 15, _d + 15)]
        for (_r, _a), _grp in _ph_d.groupby(["route_label", "airline"]):
            _price_at[(_a, _r, _d)] = float(_grp["price_jpy"].mean())

    _route_price_at = {}
    _ph_m = ph_hkg[ph_hkg["flight_date"].dt.to_period("M").astype(str) == _rev_month]
    for _d in _REV_PERIODS:
        _ph_d = _ph_m[_ph_m["days_before_dep"].between(_d - 15, _d + 15)]
        for _r, _grp in _ph_d.groupby("route_label"):
            _route_price_at[(_r, _d)] = float(_grp["price_jpy"].mean())

    _fl_snap_m = _fl_m[_fl_m["_da"].between(snap_db - _TOL, snap_db + _TOL)]
    _cnt_ser = (
        _fl_snap_m.drop_duplicates(subset=["flight_date", "airline", "route_label"])
        .groupby(["airline", "route_label"]).size()
    )

    _rev_mat = {}
    for (_a, _r), _n in _cnt_ser.items():
        _rev = 0.0
        for _d, _coef in zip(_REV_PERIODS, _coefs):
            _p = _price_at.get((_a, _r, _d)) or _route_price_at.get((_r, _d))
            if _p and not pd.isna(_p):
                _rev += _n * _rev_seats * _coef * _p
        if _rev > 0:
            _rev_mat[(_a, _r)] = int(_rev / 10_000)

    if not _rev_mat:
        st.info("選択月のデータが不足しています。データモードや観測時点を確認してください。")
    else:
        _rev_airlines = sorted({a for (a, r) in _rev_mat})
        _rev_routes   = sorted({r for (a, r) in _rev_mat})
        _ct_map_rev   = (_fl_snap_m.groupby("airline")["carrier_type"].first().to_dict()
                         if "carrier_type" in _fl_snap_m.columns else {})
        _atotals      = {a: sum(_rev_mat.get((a, r), 0) for r in _rev_routes)
                         for a in _rev_airlines}
        _rev_airlines = sorted(_rev_airlines, key=lambda a: _atotals[a], reverse=True)
        _y_rev        = [f"{a}  [LCC]" if _ct_map_rev.get(a) == "LCC" else a
                         for a in _rev_airlines]

        _z_rev = [[_rev_mat.get((_a, _r)) for _r in _rev_routes]
                  for _a in _rev_airlines]

        _rv_vals = [v for row in _z_rev for v in row if v is not None]
        _rv_min, _rv_max = (min(_rv_vals), max(_rv_vals)) if _rv_vals else (0, 1)
        _rv_rng = _rv_max - _rv_min or 1
        def _fc_rev(v):
            return "white" if (v - _rv_min) / _rv_rng > 0.65 else "black"

        _annots_rev = []
        for _i, _yl in enumerate(_y_rev):
            for _j, _r in enumerate(_rev_routes):
                _v = _z_rev[_i][_j]
                if _v is not None:
                    _annots_rev.append(dict(
                        x=_r, y=_yl,
                        text=f"¥{_v:,}万",
                        showarrow=False,
                        font=dict(size=11, color=_fc_rev(_v)),
                        xref="x", yref="y", align="center",
                    ))
                else:
                    _annots_rev.append(dict(
                        x=_r, y=_yl, text="―", showarrow=False,
                        font=dict(size=11, color="#bbb"),
                        xref="x", yref="y",
                    ))

        _fig_rev = go.Figure(go.Heatmap(
            z=_z_rev,
            x=_rev_routes,
            y=_y_rev,
            colorscale=[[0, "#F0F8FF"], [0.4, "#4DC4FF"], [0.75, "#005AFF"], [1.0, "#990099"]],
            showscale=True,
            colorbar=dict(title="万円", thickness=12, len=0.8),
            hovertemplate="<b>%{y}</b> / <b>%{x}</b><br>収益概算: ¥%{z:,}万<extra></extra>",
        ))
        _fig_rev.update_layout(
            height=max(380, len(_rev_airlines) * 48),
            xaxis=dict(title="路線", side="top"),
            yaxis=dict(title=""),
            margin=dict(l=10, r=80, t=50, b=20),
            annotations=_annots_rev,
        )
        st.plotly_chart(_fig_rev, use_container_width=True)

        _route_totals = {r: sum(_rev_mat.get((a, r), 0) for a in _rev_airlines)
                         for r in _rev_routes}
        _grand_total  = sum(_route_totals.values())
        _kpi_cols = st.columns(len(_rev_routes) + 1)
        for _kc, _r in zip(_kpi_cols, _rev_routes):
            _kc.metric(_r, f"¥{_route_totals[_r]:,}万")
        _kpi_cols[-1].metric("全路線合計", f"¥{_grand_total:,}万")

        st.caption(
            f"⚠️ 概算前提: {_rev_month} / 1便{_rev_seats}席 / "
            f"便数は出発{snap_db}日前±{_TOL}日観測の airline×flight_date ユニーク数。"
            "価格は flights / price_history の観測値（SerpAPI 推定値）。"
            "実際の需要・搭乗率・競合価格は考慮していません。"
        )
