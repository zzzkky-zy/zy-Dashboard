"""
数据加载与清洗模块 (v3 - csv-first)

数据源优先级:
  1. st.session_state['uploaded_csv_bytes']  -> 用户在看板里上传的 CSV
  2. data/products.csv                       -> 仓库内主数据
  3. /Users/yaman/Desktop/产品调研v3.2.xlsx   -> 旧版 xlsx (本地兜底)

包装图查找:
  CSV 中保留 包装图文件名 列, 看板从 data/images/<filename> 读取并转 base64。
"""
from __future__ import annotations
import base64
import io
import os
import re
from collections import Counter
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / "products.csv"
IMG_DIR = ROOT / "data" / "images"
LEGACY_XLSX = os.environ.get(
    "PRODUCT_XLSX",
    "/Users/yaman/Desktop/产品调研v3.2.xlsx",
)
EXCEL_PATH = str(CSV_PATH if CSV_PATH.exists() else LEGACY_XLSX)  # 向后兼容旧 import

# ---- 字段解析 ----------------------------------------------------------------

_NUM_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")


def _parse_sales(val) -> Optional[float]:
    if val is None: return None
    if isinstance(val, (int, float)) and not pd.isna(val): return float(val)
    s = str(val).strip()
    if s in {"", "/", "-", "nan", "None"}: return None
    if "\n" in s or ("：" in s and re.search(r"\d", s)):
        parts = re.split(r"[\n,，;；]+", s)
        nums = [_parse_sales(p.split("：")[-1]) for p in parts if p.strip()]
        nums = [n for n in nums if n]
        if len(nums) > 1: return sum(nums)
        if len(nums) == 1: return nums[0]
    has_wan = "万" in s
    m = _NUM_PATTERN.search(s.replace(",", ""))
    if not m: return None
    n = float(m.group(1))
    if has_wan: n *= 10000
    return n


def _parse_price(val) -> tuple[Optional[float], Optional[float]]:
    if val is None: return (None, None)
    if isinstance(val, (int, float)) and not pd.isna(val): return (float(val), float(val))
    s = str(val)
    if s.strip() in {"", "/", "-", "nan"}: return (None, None)
    m_ori = re.search(r"原价[^\d]*([\d.]+)", s)
    m_dis = re.search(r"优惠[^\d]*([\d.]+)", s)
    ori = float(m_ori.group(1)) if m_ori else None
    dis = float(m_dis.group(1)) if m_dis else None
    if ori is None and dis is None:
        m = _NUM_PATTERN.search(s)
        if m: ori = dis = float(m.group(1))
    if ori is None: ori = dis
    if dis is None: dis = ori
    return (ori, dis)


def _parse_unit_price(val) -> Optional[float]:
    if val is None: return None
    if isinstance(val, (int, float)) and not pd.isna(val): return float(val)
    s = str(val)
    m = re.search(r"优惠[^\d]*([\d.]+)", s)
    if m: return float(m.group(1))
    m = _NUM_PATTERN.search(s)
    return float(m.group(1)) if m else None


def _parse_volume(val) -> Optional[float]:
    if val is None: return None
    if isinstance(val, (int, float)) and not pd.isna(val): return float(val)
    m = _NUM_PATTERN.search(str(val))
    return float(m.group(1)) if m else None


def _split_words(val) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)): return []
    s = str(val).strip()
    if s in {"", "/", "-"}: return []
    parts = re.split(r"[、,，/／;；\n\s]+", s)
    return [p.strip() for p in parts if p.strip() and p.strip() not in {"/", "-"}]


# ---- 功效词归类 -------------------------------------------------------------
EFFICACY_GROUPS: dict[str, list[str]] = {
    "保湿补水": ["保湿","补水","水润","锁水","滋润","润泽","干皮","保湿因子","玻尿酸","水合"],
    "舒缓修护": ["舒缓","修护","修复","屏障","敏感肌","维稳","镇定","退红","抗敏","屏障修护","修护屏障"],
    "美白提亮": ["美白","提亮","亮肤","祛黄","淡斑","去暗沉","焕亮","显白","肤色均匀"],
    "抗老紧致": ["抗皱","抗老","紧致","提拉","抗衰","抚纹","淡纹","弹力","弹润","胶原","抚平细纹","细纹"],
    "控油去痘": ["控油","祛痘","去痘","痘印","去黑头","粉刺","毛孔","细致毛孔","净肤","去角质"],
    "清洁卸妆": ["清洁","深层清洁","卸妆","氨基酸洁面","净澈","洗净","洗卸"],
    "防晒隔离": ["防晒","隔离","防紫外线","防蓝光","防护","spf"],
    "妆效遮瑕": ["素颜","提色","提色提亮","遮瑕","上妆","妆前","服帖","雾面","自然色"],
    "肤感体验": ["温和","温和不紧绷","不紧绷","不假滑","不黏腻","清爽","轻盈","好吸收","快速吸收","易吸收","丝滑","清爽不油腻"],
    "香氛": ["留香","香氛","持久留香","淡香"],
    "唇部护理": ["丰唇","淡化唇纹","唇纹","护唇","滋养唇部"],
    "身体护理": ["身体保湿","嫩肤","全身可用"],
}
_EFFICACY_REVERSE: dict[str, str] = {}
for big, kws in EFFICACY_GROUPS.items():
    for w in kws: _EFFICACY_REVERSE[w.lower()] = big


def map_efficacy(word: str) -> str:
    if not word: return ""
    w = str(word).strip().lower()
    if w in _EFFICACY_REVERSE: return _EFFICACY_REVERSE[w]
    for kw, big in _EFFICACY_REVERSE.items():
        if kw and (kw in w or w in kw): return big
    return f"其他·{word}"


# ---- 加载 -------------------------------------------------------------------

def _img_to_data_uri(filename: str) -> str:
    if not filename: return ""
    p = IMG_DIR / filename
    if not p.exists(): return ""
    ext = p.suffix.lstrip(".").lower()
    mime = "image/jpeg" if ext in {"jpg","jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def attach_image_uris(df: pd.DataFrame) -> pd.DataFrame:
    """按需把 包装图文件名 转成 data URI; 复制 df, 不影响缓存."""
    if "包装图URI" in df.columns and df["包装图URI"].astype(bool).any():
        return df
    out = df.copy()
    if "包装图文件名" in out.columns:
        out["包装图URI"] = out["包装图文件名"].fillna("").astype(str).map(_img_to_data_uri)
    else:
        out["包装图URI"] = ""
    return out


def _enrich(full: pd.DataFrame) -> pd.DataFrame:
    """对原始 DF (csv 或 xlsx 拍平后的格式) 做派生列计算."""
    full["天猫销量"] = full.get("天猫销量原始", pd.Series(index=full.index)).map(_parse_sales)
    full["抖音销量"] = full.get("抖音销量原始", pd.Series(index=full.index)).map(_parse_sales)
    full["总销量"] = full[["天猫销量", "抖音销量"]].sum(axis=1, min_count=1)

    prices = full["天猫挂价"].map(_parse_price)
    full["原价"] = [p[0] for p in prices]
    full["优惠价"] = [p[1] for p in prices]
    full["天猫单ml价"] = full["天猫单ml"].map(_parse_unit_price) if "天猫单ml" in full else None
    full["抖音单ml价"] = full["抖音单ml"].map(_parse_unit_price) if "抖音单ml" in full else None
    full["达播价_数值"] = full["达播价"].map(_parse_unit_price) if "达播价" in full else None
    full["规格_ml"] = full["规格"].map(_parse_volume) if "规格" in full else None

    full["功效词列表"] = full["功效词"].map(_split_words) if "功效词" in full else [[] for _ in range(len(full))]
    full["功效大类"] = full["功效词列表"].map(
        lambda lst: list({map_efficacy(w) for w in lst if w})
    )
    full["香型列表"] = full["爆款香型"].map(_split_words) if "爆款香型" in full else [[] for _ in range(len(full))]

    full["品牌"] = full["品牌"].fillna("未知").astype(str).str.strip().replace({"": "未知"})
    full["产品"] = full["产品"].fillna("").astype(str).str.strip()

    # 注意: 包装图URI 不在此处生成 (开销大), 改为调用方按需 attach_image_uris()
    full["包装图URI"] = ""
    return full


def load_from_csv(path: Path | str = CSV_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = df.replace({"": pd.NA, "nan": pd.NA})
    return _enrich(df)


def load_from_csv_bytes(buf: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(buf), dtype=str, keep_default_na=False)
    df = df.replace({"": pd.NA, "nan": pd.NA})
    return _enrich(df)


def load_from_xlsx(path: str = LEGACY_XLSX) -> pd.DataFrame:
    """xlsx fallback (会现场提取嵌入图)"""
    from image_extractor import extract_package_images
    xls = pd.ExcelFile(path)
    sheets = [s for s in xls.sheet_names if s != "总"]
    images = extract_package_images(path)
    rename = {
        "天猫售量\n（累计）": "天猫销量原始",
        "抖音售量\n(累计）": "抖音销量原始",
        "规格/ml": "规格",
        "单ml": "天猫单ml",
        "单ml.1": "抖音单ml",
    }
    frames = []
    for sh in sheets:
        df = pd.read_excel(xls, sheet_name=sh).rename(columns=rename)
        df["品类"] = sh
        df["_excel_row"] = df.index + 2
        df["包装图文件名"] = df.apply(
            lambda r: Path(images.get((sh, int(r["_excel_row"])), "")).name, axis=1
        )
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    return _enrich(full)


def load_workbook(path: str | None = None) -> pd.DataFrame:
    """对外统一入口. 兼容旧的 import 名."""
    if path and str(path).endswith(".xlsx"):
        return load_from_xlsx(path)
    if CSV_PATH.exists():
        return load_from_csv(CSV_PATH)
    return load_from_xlsx(LEGACY_XLSX)


def file_signature(path: str | None = None) -> tuple:
    """缓存 key. 同时跟踪 csv 与图片目录的 mtime."""
    parts: list = []
    if CSV_PATH.exists():
        st = os.stat(CSV_PATH)
        parts.append(("csv", st.st_mtime, st.st_size))
    if IMG_DIR.exists():
        parts.append(("img", IMG_DIR.stat().st_mtime))
    if not parts and os.path.exists(LEGACY_XLSX):
        st = os.stat(LEGACY_XLSX)
        parts.append(("xlsx", st.st_mtime, st.st_size))
    return tuple(parts)


def explode_words(df: pd.DataFrame, col: str = "功效词列表") -> pd.DataFrame:
    if col not in df.columns: return pd.DataFrame()
    tmp = df[df[col].map(lambda x: isinstance(x, list) and len(x) > 0)].copy()
    tmp = tmp.explode(col).rename(columns={col: "词"})
    tmp["词"] = tmp["词"].astype(str).str.strip()
    tmp = tmp[(tmp["词"] != "") & (~tmp["词"].str.startswith("其他·"))]
    return tmp


def red_book_keywords(text: str, topk: int = 30) -> list[tuple[str, float]]:
    if not isinstance(text, str) or not text.strip(): return []
    try:
        import jieba.analyse as ja
        kws = ja.extract_tags(text, topK=topk, withWeight=True)
        return [(k, float(w)) for k, w in kws]
    except Exception:
        chunks = re.findall(r"[一-鿿]{2,}", text)
        c = Counter(chunks)
        total = sum(c.values()) or 1
        return [(w, n/total) for w, n in c.most_common(topk)]
