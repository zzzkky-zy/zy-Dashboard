"""
小红书 / 卖点词云生成器
- make_wordcloud: 标准词云
- make_dual_wordcloud: 卖点 ∪ 口碑 联合词云, 共同提到的词居中放大变红
"""
from __future__ import annotations
import os
from typing import Iterable

import numpy as np

_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]
FONT_PATH = next((f for f in _FONT_CANDIDATES if os.path.exists(f)), None)

STOP = set("的 了 是 也 有 在 和 与 但 但是 就 都 而 而且 还 又 把 被 给 让 这 那 这个 那个 一些 不 没 没有 不能 可以 会 要 像 比 之 自己 觉得 还是 一些 比较 非常 太 很 真的 我 你 他 她 我们 他们 大家 比如 一种 一类 通常 之后 之前 之间 时候 一下".split())


def _norm(weighted: Iterable[tuple[str, float]]) -> dict[str, float]:
    """归一到 0-1"""
    d = {}
    for w, v in weighted:
        if not w or w in STOP or len(w) < 2: continue
        d[w] = max(d.get(w, 0.0), float(v))
    if not d: return {}
    mx = max(d.values()) or 1.0
    return {k: v / mx for k, v in d.items()}


def make_wordcloud(text: str, weighted=None, width: int = 800, height: int = 420):
    from wordcloud import WordCloud
    if weighted is None:
        from data_loader import red_book_keywords
        weighted = red_book_keywords(text, topk=80)
    freqs = {w: max(v, 1e-3) for w, v in weighted if w and w not in STOP and len(w) >= 2}
    if not freqs: return None
    wc = WordCloud(
        font_path=FONT_PATH, width=width, height=height,
        background_color="white", colormap="plasma",
        prefer_horizontal=0.9,
        relative_scaling=0.85,   # 放大权重差异
        max_font_size=210, min_font_size=9, margin=4, collocations=False,
    )
    wc.generate_from_frequencies(freqs)
    return wc.to_image()


def make_dual_wordcloud(pitch_kws, review_kws, width: int = 900, height: int = 520):
    """
    卖点 ∪ 口碑 联合词云。
      仅卖点 -> 橙色
      仅口碑 -> 蓝色
      共同   -> 红色 + 权重×1.8 (放大居中)
    用 wordcloud.color_func 控制颜色, generate_from_frequencies 控制大小。
    """
    from wordcloud import WordCloud

    pitch = _norm(pitch_kws)
    review = _norm(review_kws)
    all_words = set(pitch) | set(review)
    if not all_words: return None

    common = set(pitch) & set(review)
    freqs: dict[str, float] = {}
    for w in all_words:
        v = max(pitch.get(w, 0), review.get(w, 0))
        if w in common:
            v = (pitch.get(w, 0) + review.get(w, 0)) * 1.8
        freqs[w] = max(v, 1e-3)

    color_map = {}
    for w in all_words:
        if w in common:
            color_map[w] = "#D62728"   # 红
        elif w in pitch:
            color_map[w] = "#FF7F0E"   # 橙
        else:
            color_map[w] = "#1F77B4"   # 蓝

    def color_func(word, *args, **kwargs):
        return color_map.get(word, "#444444")

    wc = WordCloud(
        font_path=FONT_PATH, width=width, height=height,
        background_color="white",
        prefer_horizontal=0.9, relative_scaling=0.55,
        max_font_size=160, min_font_size=12, margin=4,
        collocations=False, color_func=color_func,
    )
    wc.generate_from_frequencies(freqs)
    return wc.to_image()
