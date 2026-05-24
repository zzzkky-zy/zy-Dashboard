"""
小工具：把 Plotly 图嵌入一个 HTML 组件，监听 plotly_hover 事件
在浮动 tooltip 中渲染产品包装图。
通过 customdata 的最后一项约定为 image data URI。
"""
from __future__ import annotations
import json
import uuid

import plotly.io as pio
import streamlit.components.v1 as components


HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html,body {{ margin:0; padding:0; font-family: -apple-system, system-ui, "PingFang SC", sans-serif; }}
  #plot_{uid} {{ width: 100%; height: {height}px; }}
  #img_tip_{uid} {{
    position: fixed; pointer-events: none; z-index: 99999;
    background: white; padding: 6px; border:1px solid #ddd; border-radius:6px;
    box-shadow: 0 4px 18px rgba(0,0,0,.15); display:none;
  }}
  #img_tip_{uid} img {{ max-width: 220px; max-height: 220px; display:block; }}
  #img_tip_{uid} .lbl {{ font-size:12px; color:#333; margin-top:4px; max-width:220px; }}
</style>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
<div id="plot_{uid}"></div>
<div id="img_tip_{uid}"><img id="img_inner_{uid}" /><div class="lbl" id="lbl_{uid}"></div></div>
<script>
  const fig = {fig_json};
  const div = document.getElementById("plot_{uid}");
  Plotly.newPlot(div, fig.data, fig.layout, {{responsive:true, displaylogo:false}});

  const tip = document.getElementById("img_tip_{uid}");
  const img = document.getElementById("img_inner_{uid}");
  const lbl = document.getElementById("lbl_{uid}");

  div.on('plotly_hover', function(ev) {{
    if (!ev.points || !ev.points.length) return;
    const p = ev.points[0];
    const cd = p.customdata;
    if (!cd) return;
    const uri = cd[cd.length - 1];
    const name = cd[0] || '';
    if (uri && uri.startsWith('data:')) {{
      img.src = uri;
      lbl.textContent = name;
      tip.style.display = 'block';
    }} else {{
      tip.style.display = 'none';
    }}
  }});
  div.on('plotly_unhover', function() {{ tip.style.display = 'none'; }});

  document.addEventListener('mousemove', function(e) {{
    if (tip.style.display === 'block') {{
      let x = e.clientX + 18, y = e.clientY + 18;
      if (x + 240 > window.innerWidth) x = e.clientX - 240;
      if (y + 260 > window.innerHeight) y = e.clientY - 260;
      tip.style.left = x + 'px';
      tip.style.top = y + 'px';
    }}
  }});
</script>
</body>
</html>
"""


def plot_with_image_hover(fig, height: int = 620):
    """渲染 plotly 图并启用包装图 hover 弹层。
    要求 fig 的 trace customdata 最后一列是 base64 data URI。"""
    uid = "p" + uuid.uuid4().hex[:8]
    fig_json = pio.to_json(fig)
    html = HTML_TEMPLATE.format(uid=uid, height=height, fig_json=fig_json)
    components.html(html, height=height + 40, scrolling=False)
