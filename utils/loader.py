"""
データ読み込み・前処理ユーティリティ
BigQuery移行時はここのロード関数を置き換えるだけで対応可能
"""
import pathlib
import pandas as pd
import streamlit as st

BASE_DIR = pathlib.Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


@st.cache_data
def load_flights() -> pd.DataFrame:
    f = DATA_DIR / "flights_detail.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, encoding="utf-8-sig")
    if "is_dummy" not in df.columns:
        df["is_dummy"] = False

    carrier = load_carrier_master()
    aircraft = load_aircraft_master()

    JP_AIRPORTS = {"HND", "NRT", "KIX", "NGO", "ITM", "CTS", "FUK", "OKA",
                   "AOJ", "SDJ", "KMQ", "HIJ", "KOJ", "OIT", "KKJ", "UBJ"}
    df = df[~(df["departure_iata"].isin(JP_AIRPORTS) & df["arrival_iata"].isin(JP_AIRPORTS))]

    df["search_date"] = pd.to_datetime(df["search_date"])
    df["flight_date"] = pd.to_datetime(df["flight_date"])
    df["days_until_dep"] = (df["flight_date"] - df["search_date"]).dt.days
    df["price_jpy"] = pd.to_numeric(df["price_jpy"], errors="coerce")
    df["total_flights_on_day"] = pd.to_numeric(df["total_flights_on_day"], errors="coerce")
    df["route_lowest_price"] = pd.to_numeric(df["route_lowest_price"], errors="coerce")
    df["stops"] = pd.to_numeric(df["stops"], errors="coerce")

    df = df.merge(carrier[["airline_name", "carrier_type", "home_country"]],
                  left_on="airline", right_on="airline_name", how="left")
    df["carrier_type"] = df["carrier_type"].fillna("FSC")

    df = df.merge(aircraft[["aircraft_name", "seats", "body_type"]],
                  left_on="aircraft", right_on="aircraft_name", how="left")

    LOAD_FACTOR = 0.80
    df["est_revenue"] = (df["price_jpy"] * df["seats"] * LOAD_FACTOR).round(0)

    return df


@st.cache_data
def load_price_history() -> pd.DataFrame:
    f = DATA_DIR / "price_history.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, encoding="utf-8-sig")
    if "is_dummy" not in df.columns:
        df["is_dummy"] = False
    df["search_date"] = pd.to_datetime(df["search_date"])
    df["flight_date"] = pd.to_datetime(df["flight_date"])
    df["price_date"] = pd.to_datetime(df["price_date"])
    df["price_jpy"] = pd.to_numeric(df["price_jpy"], errors="coerce")
    df["price_change"] = pd.to_numeric(df["price_change"], errors="coerce")
    df["price_change_pct"] = pd.to_numeric(df["price_change_pct"], errors="coerce")
    return df


@st.cache_data
def load_carrier_master() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "carrier_master.csv", encoding="utf-8-sig")


@st.cache_data
def load_aircraft_master() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "aircraft_master.csv", encoding="utf-8-sig")


def latest_flights(df: pd.DataFrame) -> pd.DataFrame:
    """各 route_label × flight_date の最新 search_date のみを返す"""
    idx = df.groupby(["route_label", "flight_date"])["search_date"].idxmax()
    return df.loc[idx].reset_index(drop=True)


def route_summary(df: pd.DataFrame) -> pd.DataFrame:
    """route × flight_date 単位に集約した路線サマリーを返す"""
    latest = latest_flights(df)
    return (
        latest.groupby(["route_label", "flight_date", "departure_iata", "arrival_iata"])
        .agg(
            lowest_price=("route_lowest_price", "first"),
            price_level=("route_price_level", "first"),
            typical_low=("route_typical_low", "first"),
            typical_high=("route_typical_high", "first"),
            total_flights=("total_flights_on_day", "first"),
            min_stops=("stops", "min"),
        )
        .reset_index()
    )


PRICE_LEVEL_ORDER = ["low", "typical", "high"]
PRICE_LEVEL_COLOR = {"low": "#4DC4FF", "typical": "#F6AA00", "high": "#FF4B00"}
PRICE_LEVEL_LABEL = {"low": "低価格", "typical": "標準", "high": "高騰"}
