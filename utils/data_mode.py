"""データモード選択サイドバーウィジェット（全ページ共通）"""
import pathlib
import streamlit as st

_DUMMY_FILE = (
    pathlib.Path(__file__).parent.parent.parent / "output" / "flights_detail_dummy.csv"
)

_OPTIONS = ["combined", "real", "demo"]
_LABELS  = {
    "combined": "📊 実+ダミー（6ヶ月）",
    "real":     "✅ 実データのみ",
    "demo":     "🧪 ダミーのみ",
}
_HELP = (
    "**combined**: 実取得データ＋ダミー6ヶ月分を合算（最も広い時系列）  \n"
    "**real**: SerpAPIで実際に取得したデータのみ  \n"
    "**demo**: 再現性ありのダミーデータのみ（プレゼン用途）"
)


def data_mode_selector() -> str:
    """
    サイドバーにデータモード選択を追加してモード文字列を返す。
    ダミーファイルが未生成の場合は自動的に 'real' に固定し、案内を表示する。
    """
    dummy_ready = _DUMMY_FILE.exists()

    if not dummy_ready:
        st.sidebar.warning(
            "ダミーデータ未生成。`python scripts/06_generate_dummy.py` を実行すると"
            " combined / demo モードが使えます。",
            icon="⚠️",
        )
        st.session_state["data_mode"] = "real"
        return "real"

    default = st.session_state.get("data_mode", "combined")
    default_idx = _OPTIONS.index(default) if default in _OPTIONS else 0

    mode = st.sidebar.selectbox(
        "データモード",
        options=_OPTIONS,
        format_func=_LABELS.get,
        index=default_idx,
        help=_HELP,
    )
    st.session_state["data_mode"] = mode
    return mode
