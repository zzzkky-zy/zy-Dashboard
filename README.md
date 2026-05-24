# 📊 产品调研看板

可分享的产品调研可视化看板。任何人可访问公共 URL 浏览，授权贡献者可通过 Pull Request 更新数据。

> 数据源是 `data/products.csv`，看板基于 [Streamlit](https://streamlit.io) + Plotly。

## 📌 公共访问 (部署后)

- **看板 URL**: 部署到 [Streamlit Community Cloud](https://share.streamlit.io) 后填入此处
- **数据仓库**: 本仓库 `data/` 目录

## 🚀 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

默认 http://localhost:8501

## 🤝 如何贡献新数据

1. **下载 CSV 模板**：在公共看板左侧栏点 "📥 下载 CSV 模板"，或直接拷贝 `data/products.csv`
2. **追加你的产品行**（列名保持不变）：
   - `品类`：与现有 sheet 对齐（洁面/面护/素颜霜/唇膏/沐浴露/其他），新品类直接写新名字也会自动出现在筛选项中
   - `天猫挂价` 支持「原价：¥168\n优惠后：¥80.11」富文本写法
   - `天猫销量原始` / `抖音销量原始` 支持 `3万+` / `30万` / `6878` 等写法
   - `包装图文件名`：把图片放到 `data/images/`，文件名填入此列即可在散点悬停时显示
3. **本地预览**：`streamlit run app.py` 后在侧栏上传你修改的 CSV，立即看到新看板效果（不会污染他人）
4. **提 Pull Request**：
   - 修改 `data/products.csv`（必填）
   - 新增 `data/images/*`（如有新包装图）
   - PR 会被 review 后合并；合并后公共看板自动更新

## 🛠 一次性数据初始化

把原始 xlsx 转换为 csv + 图片：

```bash
PRODUCT_XLSX=/path/to/产品调研v3.2.xlsx python build_dataset.py
```

## ⚙️ 部署到 Streamlit Cloud

1. 把仓库 push 到 GitHub
2. 在 https://share.streamlit.io 用 GitHub 登录
3. New app → 选择本仓库与分支 → main file = `app.py`
4. 在 Secrets 里加（可选）：
   ```
   DASHBOARD_REPO_URL = "https://github.com/<owner>/<repo>"
   ```
   会让侧栏出现 "贡献新数据 → 提 PR" 直达链接
5. Deploy → 几分钟后拿到公共 URL 即可分享

## 📁 目录结构

```
product_dashboard/
├── app.py                 # 主看板
├── data_loader.py         # CSV/xlsx 解析 + 功效归类
├── hover_image.py         # 散点悬停弹包装图
├── wc_render.py           # 词云生成
├── build_dataset.py       # 一次性: xlsx → csv+images
├── requirements.txt
├── .streamlit/config.toml
└── data/
    ├── products.csv       # ★ 唯一公共数据源
    ├── products_template.csv
    └── images/            # 包装图
```
