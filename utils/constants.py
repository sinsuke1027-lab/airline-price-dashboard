"""ダッシュボード全ページ共通の色・ラベル定数（CUDO カラーユニバーサルデザイン準拠）"""

# 路線色: 青(KIX) / 朱(NGO) / 青緑(HND)  ← 赤緑の組み合わせを廃止
ROUTE_COLOR = {
    "HKG→KIX": "#005AFF",
    "HKG→NGO": "#FF4B00",
    "HKG→HND": "#03AF7A",
}

IATA_COLOR = {
    "KIX": "#005AFF",
    "NGO": "#FF4B00",
    "HND": "#03AF7A",
}

# 価格帯色: 空色(低) / オレンジ(標準) / 朱(高騰)
PRICE_COLOR = {
    "low":     "#4DC4FF",
    "typical": "#F6AA00",
    "high":    "#FF4B00",
}

PRICE_JP = {
    "low":     "低価格",
    "typical": "標準",
    "high":    "高騰",
}
