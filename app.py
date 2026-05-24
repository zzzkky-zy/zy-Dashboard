"""
产品调研看板 v3
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_loader import (
    EXCEL_PATH,
    CSV_PATH,
    EFFICACY_GROUPS,
    explode_words,
    file_signature,
    load_workbook,
    load_from_csv_bytes,
    map_efficacy,
    red_book_keywords,
)
from hover_image import plot_with_image_hover
from wc_render import make_wordcloud, make_dual_wordcloud

st.set_page_config(page_title="产品调研看板", page_icon="📊", layout="wide")

# ---- 数据加载 ---------------------------------------------------------------
@st.cache_data(show_spinner="加载数据中…")
def _load_default(sig):
    return load_workbook()


@st.cache_data(show_spinner="解析上传的 CSV…")
def _load_uploaded(content_hash: str, raw: bytes):
    return load_from_csv_bytes(raw)


def get_data() -> tuple[pd.DataFrame, str]:
    """返回 (DataFrame, 数据来源描述)。"""
    up = st.session_state.get("uploaded_csv")
    if up is not None:
        raw, name, h = up
        return _load_uploaded(h, raw), f"上传的 {name}"
    return _load_default(file_signature()), "公共数据 data/products.csv"


# ---- 顶部 -------------------------------------------------------------------
st.title("📊 产品调研看板")
df, src_label = get_data()
top_meta = ""
if CSV_PATH.exists():
    top_meta = pd.Timestamp.fromtimestamp(CSV_PATH.stat().st_mtime).strftime("%m-%d %H:%M")
st.caption(
    f"数据来源 · **{src_label}**　|　公共数据更新于 {top_meta}　"
    "|　欢迎从下方📋明细数据下载 CSV → 补充产品 → 在侧栏上传预览 → 提交 PR 让所有人看到"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("产品总数", f"{len(df):,}")
c2.metric("品牌数", df["品牌"].nunique())
c3.metric("品类数", df["品类"].nunique())
c4.metric("覆盖总销量", f"{int(df['总销量'].sum(skipna=True)):,}")
st.divider()

# ---- 侧边栏筛选 ------------------------------------------------------------
with st.sidebar:
    st.header("🤝 数据协作")
    up = st.file_uploader(
        "上传 CSV 临时预览（仅当前浏览器生效）",
        type=["csv"], key="upload_csv",
        help="按下方'下载模板'拿到 CSV → 补充产品 → 上传，看板会立刻基于新数据渲染。"
             " 不会影响公共版本，关掉浏览器即恢复。",
    )
    if up is not None:
        raw = up.getvalue()
        import hashlib as _h
        st.session_state["uploaded_csv"] = (raw, up.name, _h.md5(raw).hexdigest())
        st.success(f"已加载 {up.name}（{len(raw)/1024:.1f} KB）")
    if st.session_state.get("uploaded_csv") is not None:
        if st.button("↩ 恢复公共数据"):
            st.session_state.pop("uploaded_csv", None)
            st.rerun()

    if CSV_PATH.exists():
        st.download_button(
            "📥 下载 CSV 模板（含现有数据）",
            CSV_PATH.read_bytes(),
            file_name="products.csv", mime="text/csv",
        )
    template_path = CSV_PATH.parent / "products_template.csv"
    if template_path.exists():
        st.download_button(
            "📥 下载空白模板",
            template_path.read_bytes(),
            file_name="products_template.csv", mime="text/csv",
        )
    repo_url = os.environ.get("DASHBOARD_REPO_URL", "")
    if repo_url:
        st.markdown(
            f"🚀 **[贡献新数据 → 提 Pull Request]({repo_url}/pulls)**　"
            f"[查看仓库]({repo_url})"
        )
    else:
        st.caption("（设置环境变量 `DASHBOARD_REPO_URL` 显示仓库链接）")

    st.divider()
    st.header("🔍 筛选")
    cats = sorted(df["品类"].dropna().unique().tolist())
    sel_cat_mode = st.radio("品类", ["All"] + cats, index=0)
    sel_cats = cats if sel_cat_mode == "All" else [sel_cat_mode]
    multi_cats = st.multiselect("多品类对比 (可选)", cats, default=[])
    if multi_cats: sel_cats = multi_cats

    brand_pool = sorted(df[df["品类"].isin(sel_cats)]["品牌"].dropna().unique().tolist())
    sel_brand_mode = st.radio("品牌", ["All"] + brand_pool, index=0)
    sel_brands = brand_pool if sel_brand_mode == "All" else [sel_brand_mode]
    multi_brands = st.multiselect("多品牌对比 (可选)", brand_pool, default=[])
    if multi_brands: sel_brands = multi_brands

    use_disc = st.radio("价格采用", ["优惠价", "原价"], horizontal=True, index=0)
    sales_channel = st.radio(
        "销量口径", ["总销量", "天猫销量", "抖音销量"], horizontal=True, index=0
    )

mask = df["品类"].isin(sel_cats) & df["品牌"].isin(sel_brands)
view = df[mask].copy()
price_col = "优惠价" if use_disc == "优惠价" else "原价"

st.markdown(f"**筛选范围: {len(view)} 个产品 · {view['品牌'].nunique()} 个品牌 · "
            f"{view['品类'].nunique()} 个品类**")


# ---- 工具函数 --------------------------------------------------------------
def _humanize(n: float) -> str:
    if n is None or pd.isna(n): return ""
    n = float(n)
    if n >= 1e8: return f"{n/1e8:.2f}亿"
    if n >= 1e4: return f"{n/1e4:.1f}万"
    return f"{n:,.0f}"


def _bubble_sizeref(values, max_px: int = 48):
    """plotly 标准做法: sizeref = 2*max(values) / max_px**2 (sizemode=area)"""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0: return 1.0
    return 2.0 * float(arr.max()) / (max_px ** 2)


def _sales_axis_kwargs(series: pd.Series) -> dict:
    s = pd.Series(series).dropna()
    s = s[s > 0]
    if len(s) < 2: return {}
    return {"type": "log"} if s.max() / max(s.min(), 1) >= 50 else {}


def _tight_range(series: pd.Series, log: bool = False, pad: float = 0.08):
    """根据数据自身上下界 + 8% padding 计算 axis range。"""
    s = pd.Series(series).dropna()
    s = s[s > 0] if log else s
    if len(s) < 2: return None
    if log:
        lo, hi = np.log10(s.min()), np.log10(s.max())
        span = hi - lo
        return [lo - span * pad, hi + span * pad]
    lo, hi = float(s.min()), float(s.max())
    span = hi - lo if hi > lo else max(abs(hi) * 0.1, 1)
    return [lo - span * pad, hi + span * pad]


# ---- 页面分组 --------------------------------------------------------------
sections = st.tabs([
    "🏷 市场全景",
    "🧪 产品力",
    "🛒 渠道策略",
    "💬 产品档案 × 用户口碑",
    "📋 明细数据",
])

# ============================================================================
# 1. 市场全景
# ============================================================================
with sections[0]:
    st.subheader("品牌 · 价格 · 销量 三维分布图")
    st.caption(
        "看「谁在卖、卖多少钱、卖了多少」。把所有产品按价格(横)和销量(纵)摊开，"
        "同色气泡表示同一品牌——可识别哪些品牌占据了高价高销头部、哪些是低价爆量、"
        "哪些是冷门长尾。**悬停任一气泡可弹出该产品的真实包装图**。"
    )
    s1 = view.dropna(subset=[price_col, sales_channel]).copy()
    s1 = s1[s1[sales_channel] > 0]
    if s1.empty:
        st.info("当前筛选下无散点数据。")
    else:
        sizeref = _bubble_sizeref(s1[sales_channel].values, max_px=46)
        # 显式调色板, 保证 18+ 品牌都能拿到差异化颜色
        palette = (
            px.colors.qualitative.Light24
            + px.colors.qualitative.Dark24
            + px.colors.qualitative.Alphabet
        )
        brands_in_s1 = list(s1["品牌"].dropna().unique())
        brand_color = {b: palette[i % len(palette)] for i, b in enumerate(brands_in_s1)}

        fig = go.Figure()
        for brand, g in s1.groupby("品牌"):
            custom = np.stack([
                g["产品"].fillna("").values,
                g["品牌"].fillna("").values,
                g["品类"].fillna("").values,
                g[price_col].round(2).values,
                np.array([_humanize(v) for v in g[sales_channel].values]),
                g["包装图URI"].fillna("").values,
            ], axis=1)
            fig.add_trace(go.Scatter(
                x=g[price_col], y=g[sales_channel],
                mode="markers", name=str(brand),
                marker=dict(
                    size=g[sales_channel].clip(lower=1).values,
                    sizemode="area", sizeref=sizeref, sizemin=4,
                    color=brand_color.get(brand, "#888"),
                    opacity=0.78, line=dict(color="white", width=0.6),
                ),
                customdata=custom,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "品牌: %{customdata[1]} · 品类: %{customdata[2]}<br>"
                    "价格: ¥%{customdata[3]}<br>"
                    "销量: %{customdata[4]}<extra></extra>"
                ),
            ))
        ay = _sales_axis_kwargs(s1[sales_channel])
        fig.update_layout(
            height=620, hovermode="closest",
            xaxis_title=f"{use_disc} (¥)",
            yaxis_title=sales_channel, yaxis=ay,
            legend=dict(orientation="v", x=1.02, y=1),
        )
        plot_with_image_hover(fig, height=640)

    st.divider()
    st.subheader("整体市场 · 价格带销量结构")
    st.caption(
        "看「钱主要花在哪个价位」。把所有产品按 50 元一档分箱、销量加总，"
        "可读出整体市场的销量重心位于哪个价格带，以及不同品类在该价格带的贡献占比。"
    )
    s2 = view.dropna(subset=[price_col, sales_channel]).copy()
    if s2.empty:
        st.info("无价格数据。")
    else:
        max_p = float(s2[price_col].max())
        edges = list(range(0, int(max_p) + 50, 50)) or [0, 50]
        if edges[-1] < max_p: edges.append(int(max_p) + 50)
        labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges)-1)]
        s2["价格区间"] = pd.cut(s2[price_col], bins=edges, labels=labels,
                              include_lowest=True, right=False)
        agg = (s2.groupby(["价格区间", "品类"], observed=True)[sales_channel]
               .sum().reset_index())
        fig = px.bar(
            agg, x="价格区间", y=sales_channel, color="品类", barmode="stack",
            category_orders={"价格区间": labels},
        )
        fig.update_layout(height=460, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: 价格 50 元一档；柱内分色=各品类销量贡献。")

    st.divider()
    st.subheader("品类 · 销量主战场 vs 产品扎堆区")
    st.caption(
        "对每个品类回答两个问题：(1) **销量真正集中在哪个价格档**(🟥)、"
        "(2) **市场上 70% 的产品挤在哪个价格区间**(🟧)。"
        "若 🟥 和 🟧 错位，说明大多数品牌定价偏离了消费者真正埋单的价格 — 即定价机会窗口。"
    )
    box = view.dropna(subset=[price_col, sales_channel]).copy()
    box = box[box[sales_channel] > 0]
    if box.empty:
        st.info("无数据。")
    else:
        cats_in_view = box["品类"].unique().tolist()
        cats_sorted = sorted(
            cats_in_view,
            key=lambda c: -box[box["品类"] == c][sales_channel].sum(),
        )
        ncols = min(2, len(cats_sorted))
        cols = st.columns(ncols)
        for i, cat in enumerate(cats_sorted):
            sub = box[box["品类"] == cat]
            lo, hi = float(sub[price_col].min()), float(sub[price_col].max())
            n_bins = max(6, min(12, int(np.sqrt(len(sub) * 2))))
            edges = np.linspace(lo, hi, n_bins + 1)
            # 防止单一价位
            if edges[-1] == edges[0]:
                edges = np.array([lo - 1, lo + 1])
            bins = pd.cut(sub[price_col], bins=edges, include_lowest=True)
            agg = sub.groupby(bins, observed=True).agg(
                销量=(sales_channel, "sum"),
                产品数=(price_col, "count"),
            ).reset_index()
            agg["档中价"] = agg[price_col].apply(lambda iv: (iv.left + iv.right) / 2)
            agg["档label"] = agg[price_col].apply(lambda iv: f"¥{iv.left:.0f}-{iv.right:.0f}")
            agg = agg[agg["销量"] > 0].reset_index(drop=True)
            if agg.empty:
                continue

            peak_idx = int(agg["销量"].idxmax())
            # 70% 产品集中带: 找产品数最多的档为锚, 向两侧贪心扩展直到累计产品数 ≥ 70%
            anchor_idx = int(agg["产品数"].idxmax())
            total_n = float(agg["产品数"].sum())
            target_n = total_n * 0.7
            cum_n = float(agg.loc[anchor_idx, "产品数"])
            l, r = anchor_idx, anchor_idx
            while cum_n < target_n and (l > 0 or r < len(agg) - 1):
                left_v = agg.loc[l - 1, "产品数"] if l > 0 else -1
                right_v = agg.loc[r + 1, "产品数"] if r < len(agg) - 1 else -1
                if left_v >= right_v and l > 0:
                    l -= 1
                    cum_n += float(agg.loc[l, "产品数"])
                elif r < len(agg) - 1:
                    r += 1
                    cum_n += float(agg.loc[r, "产品数"])
                else:
                    break
            colors = ["#D9D9D9"] * len(agg)
            for k in range(l, r + 1):
                colors[k] = "#FFA94D"  # 70% 产品集中带
            colors[peak_idx] = "#E63946"  # 销量峰值

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=agg["档中价"], y=agg["销量"],
                width=(edges[1] - edges[0]) * 0.92,
                marker=dict(color=colors,
                            line=dict(color="white", width=0.5)),
                customdata=np.stack([agg["档label"], agg["产品数"]], axis=1),
                hovertemplate=(
                    "价格带: %{customdata[0]}<br>"
                    "销量加总: %{y:,}<br>"
                    "产品数: %{customdata[1]}<extra></extra>"
                ),
                showlegend=False,
            ))
            # 个体散点 (在柱顶上方薄薄一层)
            fig.add_trace(go.Scatter(
                x=sub[price_col], y=sub[sales_channel],
                mode="markers",
                marker=dict(size=7, color="rgba(30,60,120,0.55)",
                            line=dict(color="white", width=0.5)),
                text=sub["产品"],
                hovertemplate="%{text}<br>¥%{x:.0f} · 销量 %{y:,}<extra></extra>",
                name="单品", showlegend=False,
            ))
            peak_label = agg.loc[peak_idx, "档label"]
            band_label = f"{agg.loc[l, '档label'].split('-')[0]} - {agg.loc[r, '档label'].split('-')[1]}"
            fig.update_layout(
                title=f"{cat}　🟥销量最旺: {peak_label}　🟧70%产品集中: {band_label}",
                height=400, bargap=0.08,
                xaxis_title=f"{use_disc} (¥)",
                yaxis_title=f"{sales_channel} (该档加总)",
                margin=dict(t=60, b=30),
            )
            cols[i % ncols].plotly_chart(fig, use_container_width=True)
        st.caption(
            "权重逻辑: 价格按 √(2N) 自适应分档(6-12档); "
            "🟥 = 该档销量加总最大; "
            "🟧 = 从产品数最多的档向两侧贪心扩展, 直到累计产品数 ≥ 总产品数 70%（市场上 70% 产品所在价格区间）。"
        )

# ============================================================================
# 2. 产品差异化
# ============================================================================
with sections[1]:
    st.subheader("功效赛道 · 销量 vs 拥挤度")
    st.caption(
        "看「市场最买单哪类功效，以及这条赛道有多挤」。"
        "每根柱子对应一个功效大类（保湿补水 / 美白提亮 / 控油去痘 …），"
        "高度=该赛道总销量、颜色深度=该赛道在售品牌产品数。"
        "**销量高但产品数少 = 蓝海机会；销量高且颜色深 = 红海主战场；销量低颜色又深 = 内卷品类。**"
    )
    with st.expander("查看功效大类映射规则"):
        st.write({k: ", ".join(v) for k, v in EFFICACY_GROUPS.items()})

    ew = explode_words(view, "功效大类")
    if ew.empty:
        st.info("无功效词。")
    else:
        agg = ew.groupby("词").agg(
            产品数=("产品", "count"),
            总销量=(sales_channel, "sum"),
            平均销量=(sales_channel, "mean"),
            天猫销量=("天猫销量", "sum"),
            抖音销量=("抖音销量", "sum"),
        ).reset_index().sort_values("总销量", ascending=False)
        order = agg["词"].tolist()
        fig = px.bar(
            agg, x="词", y="总销量", color="产品数",
            color_continuous_scale="Tealgrn",
            hover_data={"平均销量": ":,.0f", "天猫销量": ":,.0f", "抖音销量": ":,.0f"},
            category_orders={"词": order},
        )
        fig.update_layout(height=480, xaxis_tickangle=-15)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: 同一功效大类下所有产品的销量加总；颜色深浅=该大类产品数。")

    st.divider()
    st.subheader("爆款共识词 · 销量加权卖点云")
    st.caption(
        "看「卖得好的产品都在主推什么卖点」。"
        "对每件产品的「一句话卖点」做关键词抽取，词的字号/亮度按其所属最高销量产品来决定 — "
        "**销量第一的爆款主推什么卖点，就是看板里最大最亮的词**。"
        "可作为新品文案与详情页 keyword 选型的参考。"
    )
    pitch_df = view.dropna(subset=["一句话卖点", sales_channel]).copy()
    pitch_df = pitch_df[pitch_df[sales_channel] > 0]
    if pitch_df.empty:
        st.info("无卖点数据。")
    else:
        # 改为 max 策略: 每个词的权重 = 提到它的产品中最高销量
        # 再做 1.5 次幂放大: 让头部产品的词在词云里彻底压倒尾部
        word_sales: dict[str, float] = {}
        for _, r in pitch_df.iterrows():
            text = str(r["一句话卖点"])
            sale = float(r[sales_channel])
            kws = red_book_keywords(text, topk=12)
            for w, _w in kws:
                if len(w) >= 2:
                    if sale > word_sales.get(w, 0.0):
                        word_sales[w] = sale
        if word_sales:
            weighted = sorted(
                ((w, s ** 1.5) for w, s in word_sales.items()),
                key=lambda x: -x[1],
            )[:80]
            img = make_wordcloud("", weighted=weighted, width=900, height=440)
            if img: st.image(img, use_container_width=True)
        st.caption("权重 = (该词所属最高销量产品的销量)^1.5；销量第一的产品 — 它的卖点关键词会最大、最居中、最亮。")

    st.divider()
    st.subheader("性价比 vs 销量表现矩阵（单ml单价口径）")
    st.caption(
        "看「单价高低对销量到底有没有影响」。"
        "横轴单ml单价、纵轴销量，**两条灰色中位线把图分成 4 象限**：左上=高性价比爆款、"
        "右上=高单价仍能高销的品牌力产品、左下=平价长尾、右下=高单价但销量也未起来的溢价产品。"
        "气泡按品牌着色，可观察同品牌的产品落在哪个象限。"
    )
    sm = view.dropna(subset=["天猫单ml价", sales_channel]).copy()
    sm = sm[(sm["天猫单ml价"] > 0) & (sm[sales_channel] > 0)]
    if sm.empty:
        st.info("无单ml数据。")
    else:
        med_x = float(sm["天猫单ml价"].median())
        med_y = float(sm[sales_channel].median())
        # 量级判断
        x_log = sm["天猫单ml价"].max() / max(sm["天猫单ml价"].min(), 1e-3) >= 30
        y_log = sm[sales_channel].max() / max(sm[sales_channel].min(), 1) >= 50
        sizeref = _bubble_sizeref(sm[sales_channel].values, max_px=40)
        fig = px.scatter(
            sm, x="天猫单ml价", y=sales_channel, color="品牌",
            hover_name="产品", hover_data=["品类", "规格_ml", price_col],
            size=sm[sales_channel].clip(lower=1).values,
            size_max=40,
            log_x=x_log, log_y=y_log,
        )
        fig.add_vline(x=med_x, line_dash="dot", line_color="grey",
                      annotation_text=f"中位单ml价 ¥{med_x:.2f}",
                      annotation_position="top")
        fig.add_hline(y=med_y, line_dash="dot", line_color="grey",
                      annotation_text=f"中位销量 {_humanize(med_y)}",
                      annotation_position="right")
        x_range = _tight_range(sm["天猫单ml价"], log=x_log)
        y_range = _tight_range(sm[sales_channel], log=y_log)
        fig.update_layout(
            height=560,
            xaxis_title=f"天猫优惠单 ml 价 (¥/ml{', log' if x_log else ''})",
            yaxis_title=f"{sales_channel}{'  (log)' if y_log else ''}",
            xaxis=dict(range=x_range) if x_range else {},
            yaxis=dict(range=y_range) if y_range else {},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: 气泡尺寸=销量；坐标轴范围按数据自身边界 ±8% 自动收紧。")

    st.divider()
    st.subheader("品牌定位地图 · 价位 vs 销量")
    st.caption(
        "把每个品牌看作一个点，用「爆品平均价」表示其市场定位、用「总销量」表示其市场规模。"
        "中位线分出 4 个定位象限：**右上 高价高销头部 · 左上 低价爆量 · 右下 高价定位品 · 左下 低价长尾**。"
        "用于回答：我们的目标定价区间里，谁是直接对手、谁是参照系？"
    )
    bm = view.dropna(subset=[price_col, sales_channel]).copy()
    bm = bm[bm[sales_channel] > 0]
    bm_agg = bm.groupby("品牌").agg(
        爆品平均价=(price_col, "mean"),
        总销量=(sales_channel, "sum"),
        爆品数=(price_col, "count"),
    ).reset_index().dropna()
    if bm_agg.empty:
        st.info("无数据。")
    else:
        y_log = bm_agg["总销量"].max() / max(bm_agg["总销量"].min(), 1) >= 50
        med_x = float(bm_agg["爆品平均价"].median())
        med_y = float(bm_agg["总销量"].median())

        palette = (
            px.colors.qualitative.Light24
            + px.colors.qualitative.Dark24
            + px.colors.qualitative.Alphabet
        )
        bm_agg = bm_agg.sort_values("总销量", ascending=False).reset_index(drop=True)
        brand_color = {b: palette[i % len(palette)] for i, b in enumerate(bm_agg["品牌"])}

        fig = go.Figure()
        for _, row in bm_agg.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["爆品平均价"]], y=[row["总销量"]],
                mode="markers+text",
                marker=dict(size=20, color=brand_color[row["品牌"]],
                            line=dict(color="white", width=1.5)),
                text=[row["品牌"]], textposition="top center",
                name=row["品牌"],
                customdata=[[row["爆品数"]]],
                hovertemplate=(
                    "<b>%{text}</b><br>爆品平均价: ¥%{x:.2f}<br>"
                    "总销量: %{y:,}<br>爆品数: %{customdata[0]}<extra></extra>"
                ),
            ))
        # 中位分割线 + 象限注解
        fig.add_vline(x=med_x, line_dash="dot", line_color="grey",
                      annotation_text=f"中位价 ¥{med_x:.0f}",
                      annotation_position="top")
        fig.add_hline(y=med_y, line_dash="dot", line_color="grey",
                      annotation_text=f"中位销量 {_humanize(med_y)}",
                      annotation_position="right")
        fig.update_layout(
            height=600,
            xaxis_title=f"爆品 {use_disc} 平均 (¥)",
            yaxis_title=f"总销量{' (log)' if y_log else ''}",
            yaxis=dict(type="log") if y_log else {},
            showlegend=True,
            legend=dict(orientation="v", x=1.02, y=1, font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: 不使用产品数作权重 — 仅在 hover 信息中提示爆品数。颜色仅用于区分品牌。")

# ============================================================================
# 3. 渠道策略
# ============================================================================
with sections[2]:
    st.subheader("品类 · 渠道倾向（淘宝 vs 抖音）")
    st.caption(
        "看「每个品类的销量主战场是淘宝还是抖音」。"
        "品类按整体销量降序排列；同一品类下两根柱直接对比双渠道销量。"
        "下方表格补充淘抖各自占比，用于判断进货/投放/直播侧重哪一端。"
    )
    ch = view.groupby("品类").agg(
        淘宝销量=("天猫销量", "sum"),
        抖音销量=("抖音销量", "sum"),
        产品数=("产品", "count"),
    ).reset_index()
    ch["合计"] = ch["淘宝销量"] + ch["抖音销量"]
    ch = ch.sort_values("合计", ascending=False)
    if ch.empty:
        st.info("无数据。")
    else:
        order = ch["品类"].tolist()
        long = ch.melt(id_vars=["品类"], value_vars=["淘宝销量", "抖音销量"],
                       var_name="渠道", value_name="销量")
        fig = px.bar(
            long, x="品类", y="销量", color="渠道", barmode="group",
            category_orders={"品类": order},
            color_discrete_map={"淘宝销量": "#FF6F00", "抖音销量": "#000000"},
            text_auto=".2s",
        )
        fig.update_layout(height=480)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: X 轴按品类合计销量降序；表格补充淘抖占比。")

        ch["淘宝占比"] = ch["淘宝销量"] / ch["合计"].replace(0, pd.NA)
        ch["抖音占比"] = 1 - ch["淘宝占比"]
        st.dataframe(
            ch[["品类","淘宝销量","抖音销量","合计","淘宝占比","抖音占比","产品数"]]
                .style.format({
                    "淘宝销量":"{:,.0f}", "抖音销量":"{:,.0f}", "合计":"{:,.0f}",
                    "淘宝占比":"{:.1%}", "抖音占比":"{:.1%}",
                }),
            use_container_width=True,
        )

    st.divider()
    st.subheader("品牌 · 渠道结构画像")
    st.caption(
        "看「每个品牌主要靠哪个渠道走量」。堆叠柱按品牌总销量降序排列；"
        "橙黑两段比例直观显示该品牌是淘宝主力、抖音主力，还是双渠道平衡型。"
        "可用于品牌渠道战略分析与对手渠道布局判断。"
    )
    bch = view.groupby("品牌").agg(
        淘宝销量=("天猫销量", "sum"), 抖音销量=("抖音销量", "sum"),
    ).reset_index()
    bch["合计"] = bch["淘宝销量"] + bch["抖音销量"]
    bch = bch[bch["合计"] > 0].sort_values("合计", ascending=False)
    if not bch.empty:
        order = bch["品牌"].tolist()
        fig = px.bar(
            bch.melt(id_vars="品牌", value_vars=["淘宝销量","抖音销量"],
                     var_name="渠道", value_name="销量"),
            x="品牌", y="销量", color="渠道", barmode="stack",
            category_orders={"品牌": order},
            color_discrete_map={"淘宝销量": "#FF6F00", "抖音销量": "#000000"},
        )
        fig.update_layout(height=480, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: X 轴按品牌总销量降序；柱内橙=淘宝销量，黑=抖音销量。")

    st.divider()
    st.subheader("价格带 · 渠道偏好曲线")
    st.caption(
        "回答两个核心问题：**(1) 低价产品是否真的更适合抖音？(2) 高价产品是否更依赖淘宝？** "
        "横轴按天猫价 50 元一档；柱高=该档双渠道销量；蓝线（右轴）=该档抖音占比。"
        "若蓝线在低价段攀高、在高价段下沉，则验证「价格越低、抖音权重越大」的假设。"
    )
    pc = view.dropna(subset=[price_col]).copy()
    pc = pc[(pc[price_col] > 0) & ((pc["天猫销量"].fillna(0) + pc["抖音销量"].fillna(0)) > 0)]
    if pc.empty:
        st.info("无可对比数据。")
    else:
        max_p = float(pc[price_col].max())
        edges = list(range(0, int(max_p) + 50, 50)) or [0, 50]
        if edges[-1] < max_p:
            edges.append(int(max_p) + 50)
        labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
        pc["价格带"] = pd.cut(pc[price_col], bins=edges, labels=labels,
                            include_lowest=True, right=False)
        agg = pc.groupby("价格带", observed=True).agg(
            淘宝销量=("天猫销量", "sum"),
            抖音销量=("抖音销量", "sum"),
            产品数=(price_col, "count"),
        ).reset_index()
        agg = agg[(agg["淘宝销量"] + agg["抖音销量"]) > 0]
        agg["合计"] = agg["淘宝销量"] + agg["抖音销量"]
        agg["抖音占比"] = agg["抖音销量"] / agg["合计"].replace(0, pd.NA)

        long = agg.melt(id_vars=["价格带", "产品数"],
                        value_vars=["淘宝销量", "抖音销量"],
                        var_name="渠道", value_name="销量")
        fig = go.Figure()
        for ch_name, color in [("淘宝销量", "#FF6F00"), ("抖音销量", "#000000")]:
            sub = long[long["渠道"] == ch_name]
            fig.add_trace(go.Bar(
                x=sub["价格带"], y=sub["销量"], name=ch_name,
                marker_color=color, opacity=0.85,
                customdata=sub[["产品数"]].values,
                hovertemplate=(
                    "价格带 ¥%{x}<br>" + ch_name + ": %{y:,}<br>"
                    "档内产品数: %{customdata[0]}<extra></extra>"
                ),
            ))
        # 抖音占比折线 (副 y 轴)
        fig.add_trace(go.Scatter(
            x=agg["价格带"], y=agg["抖音占比"],
            mode="lines+markers+text",
            name="抖音占比",
            line=dict(color="#1F77B4", width=2),
            marker=dict(size=8),
            text=[f"{v:.0%}" if pd.notna(v) else "" for v in agg["抖音占比"]],
            textposition="top center",
            yaxis="y2",
            hovertemplate="价格带 ¥%{x}<br>抖音占比: %{y:.1%}<extra></extra>",
        ))
        fig.update_layout(
            barmode="group", height=560,
            xaxis=dict(title=f"{use_disc}价格带 (¥)",
                       categoryorder="array", categoryarray=labels),
            yaxis=dict(title="销量 (淘宝 / 抖音)"),
            yaxis2=dict(title="抖音占比", overlaying="y", side="right",
                        tickformat=".0%", range=[0, 1.05], showgrid=False),
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: 价格统一按天猫价分档；柱高 = 该档内所有产品在对应渠道的销量加总；"
                   "蓝线 = 抖音销量 / 合计销量。占比越接近 100% 表示该价格带越依赖抖音。")

    st.divider()
    st.subheader("功效赛道 · 渠道吸引力")
    st.caption(
        "看「不同功效在淘宝、抖音上各自的卖货能力」。上图为 Top 20 功效大类的双渠道销量直接对比，"
        "下图为同一组功效的「抖音偏好度」（−1 = 纯靠淘宝、+1 = 纯靠抖音），"
        "用以快速判断某一功效卖点在哪个渠道更容易撬动转化。"
    )
    ew = explode_words(view, "功效大类")
    if not ew.empty:
        agg = ew.groupby("词").agg(
            淘宝销量=("天猫销量", "sum"), 抖音销量=("抖音销量", "sum"),
        ).reset_index()
        agg["合计"] = agg["淘宝销量"] + agg["抖音销量"]
        agg = agg.sort_values("合计", ascending=False).head(20)
        order = agg["词"].tolist()
        fig = px.bar(
            agg.melt(id_vars="词", value_vars=["淘宝销量","抖音销量"],
                     var_name="渠道", value_name="销量"),
            x="词", y="销量", color="渠道", barmode="group",
            category_orders={"词": order},
            color_discrete_map={"淘宝销量": "#FF6F00", "抖音销量": "#000000"},
        )
        fig.update_layout(height=520, xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("权重逻辑: Top 20 功效大类按双渠道合计销量降序选取；柱内橙=淘宝，黑=抖音。")

        agg["抖音偏好度"] = (agg["抖音销量"] - agg["淘宝销量"]) / agg["合计"].replace(0,1)
        agg = agg.sort_values("抖音偏好度")
        fig2 = px.bar(
            agg, x="抖音偏好度", y="词", orientation="h",
            color="抖音偏好度", color_continuous_scale="RdBu_r",
            hover_data={"淘宝销量":":,", "抖音销量":":,", "合计":":,"},
        )
        fig2.update_layout(height=600)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("权重逻辑: 抖音偏好度 = (抖音销量 − 淘宝销量) / (淘宝+抖音)；−1=纯淘宝, +1=纯抖音。")

# ============================================================================
# 4. 产品详情 + 用户口碑
# ============================================================================
with sections[3]:
    st.subheader("产品档案 · 卖点 vs 用户口碑")
    st.caption(
        "选择某一具体产品，把它的「品牌想说的（一句话卖点）」与「用户实际感受到的（小红书评价）」摆在一起。"
        "联合词云中，**两端共同提到的词被放大置中，提示「品牌卖点是否真正击中了用户感知」**；"
        "只在某一端出现的词则反映卖点失语或用户痛点未被官方文案覆盖。"
    )
    pool = view.dropna(subset=["产品"]).copy()
    pool = pool[(pool["一句话卖点"].notna()) | (pool["小红书用户评价"].notna())]
    pool = pool.sort_values(sales_channel, ascending=False, na_position="last")
    if pool.empty:
        st.info("当前筛选下无产品文本数据。")
    else:
        labels = pool.apply(
            lambda r: f"[{r['品类']}] {r['品牌']} - {r['产品']}", axis=1
        ).tolist()
        idx = st.selectbox(
            "选择产品",
            options=list(range(len(pool))),
            format_func=lambda i: labels[i],
        )
        chosen = pool.iloc[idx]
        pitch = str(chosen["一句话卖点"]) if pd.notna(chosen["一句话卖点"]) else ""
        review = str(chosen["小红书用户评价"]) if pd.notna(chosen["小红书用户评价"]) else ""
        uri = chosen.get("包装图URI", "")

        cleft, cmid, cright = st.columns([1, 1.4, 2.2])
        with cleft:
            st.markdown("##### 包装图")
            if uri:
                st.image(uri, use_container_width=True)
            else:
                st.caption("(无包装图)")
            st.markdown(f"**品牌**　{chosen['品牌']}")
            st.markdown(f"**品类**　{chosen['品类']}")
            st.markdown(f"**规格**　{chosen.get('规格', '/')}")
            if pd.notna(chosen.get(price_col)):
                st.markdown(f"**{use_disc}**　¥{float(chosen[price_col]):.2f}")
            st.markdown(f"**天猫销量**　{_humanize(chosen.get('天猫销量', 0))}")
            st.markdown(f"**抖音销量**　{_humanize(chosen.get('抖音销量', 0))}")

        with cmid:
            st.markdown("##### 一句话卖点")
            st.write(pitch or "_(无卖点文本)_")
            st.markdown("##### 小红书用户评价")
            st.write(review or "_(无评价文本)_")

        with cright:
            st.markdown("##### 卖点 × 口碑 联合词云")
            st.caption("橙色=仅卖点提到 · 蓝色=仅口碑提到 · 红色加大居中=两者**共同提到**。")
            pitch_kws = red_book_keywords(pitch, topk=40) if pitch else []
            review_kws = red_book_keywords(review, topk=60) if review else []
            img = make_dual_wordcloud(pitch_kws, review_kws, width=900, height=520)
            if img:
                st.image(img, use_container_width=True)
            else:
                st.caption("(无可视化文本)")
            st.caption("权重逻辑: 各自用 jieba TF-IDF 评分 → 标准化到 0-1; "
                       "**两端都提到的词权重相加并 ×1.8 加权**, 字号最大、红色高亮、放在画布中心。")

        st.divider()
        st.markdown("##### 当前筛选范围 · 用户共鸣词云")
        st.caption(
            "把当前筛选下所有产品的小红书评价拼接重做关键词抽取，"
            "可观察到该品类/品牌人群在意的共性话题（味道、肤感、性价比、副作用等），"
            "辅助产品定位与传播主题选型。"
        )
        all_text = "\n".join(
            pool["小红书用户评价"].dropna().astype(str).tolist()
        )
        if all_text.strip():
            kws = red_book_keywords(all_text, topk=120)
            big = make_wordcloud(all_text, weighted=kws, width=1200, height=520)
            if big: st.image(big, use_container_width=True)
            st.caption("权重逻辑: jieba TF-IDF。")

# ============================================================================
# 5. 数据表
# ============================================================================
with sections[4]:
    st.subheader("筛选范围明细 · 可下载")
    st.caption(
        "当前筛选范围内所有产品的字段级明细，按总销量降序。"
        "可一键下载为 CSV 用于线下进一步分析；"
        "也可作为模板补充新产品后从侧栏上传预览，或推回 GitHub 仓库更新公共版本。"
    )
    with st.expander("🤝 如何贡献新数据 / 把改动同步回公共看板"):
        st.markdown("""
1. 在左侧栏点击 **下载 CSV 模板（含现有数据）** 或 **下载空白模板**
2. 在 Excel/Numbers 里追加你新调研的产品行，**列名保持不变**
   - 价格列 `天猫挂价` 支持「原价：¥168\\n优惠后：¥80.11」这种富文本
   - 销量列 `天猫销量原始` / `抖音销量原始` 支持 `3万+`/`30万`/`6878` 等写法
   - 包装图：把图片文件放到 `data/images/` 目录，并在 `包装图文件名` 列里填入文件名
3. 把更新后的 CSV 拖到左侧栏 **上传 CSV** 区域，看板会立即用新数据渲染（仅当前浏览器，关浏览器即恢复）
4. 满意后向项目仓库提交 Pull Request：
   - **修改的文件**：`data/products.csv`（必）+ `data/images/*`（如新增图）
   - 仓库管理员合并后，所有访问公共看板的人都会看到更新
        """)
    show_cols = ["品类","品牌","产品","规格_ml","原价","优惠价","天猫单ml价","达播价_数值",
                 "天猫销量","抖音销量","总销量","功效词","爆款香型","一句话卖点"]
    show_cols = [c for c in show_cols if c in view.columns]
    st.dataframe(
        view[show_cols].sort_values("总销量", ascending=False, na_position="last"),
        use_container_width=True, height=620,
    )
    st.download_button(
        "下载筛选 CSV",
        view[show_cols].to_csv(index=False).encode("utf-8-sig"),
        "filtered.csv", "text/csv",
    )
