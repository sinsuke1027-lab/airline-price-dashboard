import streamlit as st
import pandas as pd
from utils.loader import load_flights, load_price_history, route_summary, latest_flights

st.set_page_config(page_title="路線誘致 分析ダッシュボード", layout="wide", page_icon="✈️")

st.title("✈️ 路線誘致 分析ダッシュボード")
st.caption("「どの路線を・誰に・なぜ売り込むか」をデータで答えるための分析ツール")

flights  = load_flights()
summary  = route_summary(flights)
df_latest = latest_flights(flights)

# ===== NGO路線サマリー =====
TARGET = "NGO"
dep_iata = df_latest["departure_iata"].mode().iloc[0] if not df_latest.empty else "HKG"
dep_label = f"{dep_iata}→{TARGET}"

ngo_summary = summary[summary["arrival_iata"] == TARGET].copy()
all_summary = summary.copy()

# --- KPI計算 ---
LOAD_FACTOR = 0.80

if not ngo_summary.empty:
    total_days  = len(ngo_summary)
    high_days   = (ngo_summary["price_level"] == "high").sum()
    high_rate   = high_days / total_days if total_days > 0 else 0
    avg_price   = ngo_summary["lowest_price"].mean()
    avg_typ_low  = ngo_summary["typical_low"].mean()
    avg_typ_high = ngo_summary["typical_high"].mean()
    avg_typical  = (avg_typ_low + avg_typ_high) / 2 if pd.notna(avg_typ_low) and pd.notna(avg_typ_high) else None
    price_gap    = avg_price - avg_typical if avg_typical else None
    avg_flights_ngo = ngo_summary["total_flights"].mean()

    # KIX比較用
    kix_summary = summary[summary["arrival_iata"] == "KIX"]
    avg_flights_kix = kix_summary["total_flights"].mean() if not kix_summary.empty else None

    # 誘致ターゲット数（他路線に就航しているがNGO未就航の航空会社）
    ngo_airlines = set(df_latest[df_latest["arrival_iata"] == TARGET]["airline"].unique())
    other_airlines = set(df_latest[df_latest["arrival_iata"] != TARGET]["airline"].unique())
    target_count = len(other_airlines - ngo_airlines)
else:
    high_rate = high_days = total_days = 0
    avg_price = avg_typical = price_gap = None
    avg_flights_ngo = avg_flights_kix = None
    target_count = 0

# ===== KPIカード（NGO特化） =====
st.subheader(f"📍 {dep_label} 現状サマリー")
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    f"{dep_label} 価格高騰率",
    f"{high_rate*100:.0f}%",
    delta=f"{high_days}/{total_days}日が高価格水準" if total_days > 0 else "-",
    help="観測期間中にprice_level=highだった日の割合。50%超は構造的需要過多のシグナル。"
)

if avg_flights_kix is not None:
    diff = avg_flights_ngo - avg_flights_kix
    c2.metric(
        f"{dep_iata}→NGO 平均便数/日",
        f"{avg_flights_ngo:.1f} 便",
        delta=f"KIX比 {diff:+.1f}",
        delta_color="inverse",
        help="KIXより少ない便数は「NGO参入余地あり」の根拠になる。"
    )
else:
    c2.metric(f"{dep_iata}→NGO 平均便数/日", f"{avg_flights_ngo:.1f} 便" if avg_flights_ngo else "-")

if price_gap is not None:
    c3.metric(
        "typical価格との乖離",
        f"¥{price_gap:+,.0f}",
        delta="実勢価格 > typical" if price_gap > 0 else "実勢価格 ≤ typical",
        delta_color="inverse" if price_gap > 0 else "normal",
        help="route_typical_low/highの中央値と実際の最安値の差。プラスなら需要が標準水準を超えている。"
    )
else:
    c3.metric("typical価格との乖離", "-", help="typical価格データが不足しています。")

c4.metric(
    "誘致ターゲット候補社数",
    f"{target_count} 社",
    help=f"{dep_iata}路線で他空港には就航しているが{TARGET}未就航の航空会社数。"
)

# ===== 自動生成 提案ピッチ文 =====
st.divider()
st.subheader("📝 自動生成 提案ピッチ文（コピー用）")
st.caption("以下の文章はデータから自動生成された叩き台です。数値と文脈を確認のうえ、提案書に転記してください。")

pitch_lines = []
if high_rate >= 0.5:
    pitch_lines.append(
        f"・{dep_label}路線において、観測期間{total_days}日中{high_days}日（{high_rate*100:.0f}%）が"
        f"高価格水準（price_level: high）を記録しています。"
        f"これは {TARGET} への旅客需要が構造的に供給を上回っていることを示すシグナルです。"
    )
elif high_rate > 0:
    pitch_lines.append(
        f"・{dep_label}路線において、観測期間{total_days}日中{high_days}日（{high_rate*100:.0f}%）で"
        f"高価格水準が観測されています。需要の高まりが始まっており、就航の好機と判断できます。"
    )
else:
    pitch_lines.append(
        f"・{dep_label}路線は現時点で価格高騰の観測なし。需要の継続的モニタリングを推奨します。"
    )

if price_gap is not None and price_gap > 0:
    pitch_lines.append(
        f"・現在の実勢最安値（平均 ¥{avg_price:,.0f}）は SerpAPI の標準価格帯"
        f"（¥{avg_typ_low:,.0f}〜¥{avg_typ_high:,.0f}）を ¥{price_gap:,.0f} 上回っており、"
        f"旅客は需要過多による割高な運賃を支払っている状況です。"
    )

if avg_flights_kix is not None and avg_flights_ngo < avg_flights_kix:
    pitch_lines.append(
        f"・{dep_iata}→KIX の平均 {avg_flights_kix:.1f} 便/日に対し、{dep_iata}→NGO は"
        f" {avg_flights_ngo:.1f} 便/日と{avg_flights_kix - avg_flights_ngo:.1f} 便/日少なく、"
        f"中部エリアへの供給不足が明確です。増便・新規就航の余地が大きいと考えられます。"
    )

if target_count > 0:
    pitch_lines.append(
        f"・{dep_iata}路線で他空港には就航しているが {TARGET} に未就航の航空会社は {target_count} 社。"
        f"これらは同一出発地での運航実績があり、{TARGET} への就航コストが相対的に低い誘致候補です。"
    )

if pitch_lines:
    pitch_text = "\n".join(pitch_lines)
    st.text_area("提案ピッチ文（叩き台）", pitch_text, height=180, key="pitch_box")
    st.caption("⚠️ 座席数・収益試算はダミー値を含みます。提案書への記載時は必ず仮定条件を明記してください。")
else:
    st.info("十分なデータが収集できていません。データが蓄積されると自動的に文章が生成されます。")

# ===== 需要の構造的シグナル =====
st.divider()
st.subheader("⚠️ 需要の構造的シグナル")
st.caption("価格が高い・直行便がない = 旅客の需要に供給が追いついていない。路線誘致提案の根拠として活用できます。")

high_routes = all_summary[all_summary["price_level"] == "high"]
alert_count = len(high_routes)
if alert_count > 0:
    route_list = "・".join(
        f"{r['route_label']}（{r['flight_date'].strftime('%m/%d')}）"
        for _, r in high_routes.head(10).iterrows()
    )
    st.error(f"🔴 **価格が継続的に高い路線・日付: {alert_count} 件** — {route_list}")
    st.caption("→ B-3「便数 vs 価格」または E-2「路線開拓ランキング」で構造的な需要過多を確認してください。")
else:
    st.success("🟢 現在、高価格水準の路線はありません。")

no_direct = [r for r in flights["route_label"].unique()
             if df_latest[df_latest["route_label"] == r]["stops"].min() > 0]
if no_direct:
    st.warning(f"🟡 **直行便が存在しない路線: {len(no_direct)} 路線** — {', '.join(no_direct)}")
    st.caption("→ B-2「直行便空白路線」で新規就航の機会を確認してください。")

st.divider()

# ===== 分析の進め方ガイド =====
st.subheader("🗺️ 分析の進め方")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
**STEP 1｜現状を把握する**

| ページ | 問い |
|--------|------|
| 📅 A-1 価格カレンダー | いつ・どの路線が高い？ |
| 🕐 A-3 時間帯別分布 | 空いている時間帯はどこ？ |

**STEP 2｜機会を発見する**

| ページ | 問い |
|--------|------|
| 🔍 B-2 直行便空白路線 | 直行便がないのに高い路線は？ |
| 📊 B-3 便数 vs 価格 | 供給不足な路線はどこ？ |
| 📈 B-5 価格・需要トレンド分析 | 需要は継続的に高いか？ |
""")
with col2:
    st.markdown("""
**STEP 3｜競合を比較する**

| ページ | 問い |
|--------|------|
| 🏆 C-1 競合空港比較 | 自空港は競合より劣っているか？ |
| ✈️ C-3 誘致ターゲット分析 | 誰を誘致すべきか？ |

**STEP 4｜優先順位を決める**

| ページ | 問い |
|--------|------|
| 🥇 E-2 路線開拓ランキング | 次シーズンの交渉で最優先の路線はどれ？ |
""")

st.divider()
st.caption("左サイドバーの各ページから分析を進めてください。各分析は次シーズンの就航・増便交渉に向けた提案材料の構築を目的としています。")
