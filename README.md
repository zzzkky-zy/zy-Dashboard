# 📊 产品调研看板

把 `data/products.csv` 里的产品数据可视化成 5 大类分析看板（市场全景 / 产品力 / 渠道策略 / 产品档案+用户口碑 / 明细数据），可在本地浏览器打开使用，也可部署到公网。

> 数据可以随时编辑（CSV + 图片），看板会自动更新。无需懂任何代码即可日常维护。

---

## 1️⃣ 这是什么 / 你能用它做什么

- **可视化产品调研结果**：价格分布、销量赛道、品牌定位、渠道偏好、卖点 vs 用户口碑等共 12 张图
- **直接编辑 CSV 即可更新数据**：不需要懂 Python，用 Excel/Numbers 改 `data/products.csv` 保存即可
- **新增产品时支持插入包装图**：把图放到 `data/images/` 目录，并在 CSV 对应行的「包装图文件名」列填上文件名
- **支持新增品类、新增品牌**：CSV 里直接加新行、写新名字，看板筛选项自动出现

---

## 2️⃣ 系统要求

| 系统 | 最低要求 |
|---|---|
| **macOS** | 10.15+（推荐 12+） |
| **Windows** | 10/11 |
| **Python** | 3.10 ~ 3.12（**不要用 3.13**，部分依赖未支持） |
| **磁盘** | 约 200 MB（依赖包） + 数据本身 |
| **内存** | 2 GB 可用即可 |
| **联网** | 仅首次安装依赖时需要联网 |

---

## 3️⃣ 一次性安装（约 10 分钟）

### 第 1 步：装 Python

**macOS**：
```bash
# 检查是否已装
python3 --version
# 如果没装或版本 <3.10，去 https://www.python.org/downloads/ 下载安装包
# 推荐 Python 3.11 或 3.12
```

**Windows**：
- 去 [python.org/downloads](https://www.python.org/downloads/) 下载 3.11 或 3.12
- ⚠️ 安装时**务必勾选 "Add Python to PATH"**
- 装完打开"命令提示符" 或 PowerShell，跑 `python --version` 验证

### 第 2 步：下载项目

**方式 A：从 GitHub 直接下载**
1. 打开仓库 → 点绿色 **Code** 按钮 → **Download ZIP**
2. 解压到自己想放的位置，例如：
   - macOS: `~/Documents/zy-Dashboard`
   - Windows: `C:\Users\你的用户名\Documents\zy-Dashboard`

**方式 B：用 git 克隆（懂 git 的话）**
```bash
git clone https://github.com/zzzkky-zy/zy-Dashboard.git
cd zy-Dashboard
```

### 第 3 步：安装依赖包

打开终端（macOS）/ 命令提示符（Windows），切到项目目录：

```bash
# macOS / Linux
cd ~/Documents/zy-Dashboard

# Windows (PowerShell)
cd C:\Users\你的用户名\Documents\zy-Dashboard
```

然后跑：
```bash
# macOS / Linux
python3 -m pip install -r requirements.txt

# Windows
python -m pip install -r requirements.txt
```

等待 2-3 分钟下载安装。看到 `Successfully installed ...` 就成功了。

> 如果某一步报错 `pip not found`，先跑 `python3 -m ensurepip --upgrade`（Mac）或 `python -m ensurepip --upgrade`（Windows）

---

## 4️⃣ 启动看板

每次想用的时候，打开终端进入项目目录，跑：

```bash
# macOS / Linux
python3 -m streamlit run app.py

# Windows
python -m streamlit run app.py
```

终端会显示：
```
You can now view your Streamlit app in your browser.
Local URL:  http://localhost:8501
```

浏览器会自动打开 `http://localhost:8501`，看板就出现了。

**关闭**：在终端按 `Ctrl + C`（Windows/Linux）或 `Control + C`（Mac）。

---

## 5️⃣ 日常使用：怎么更新数据

### 场景 A：调研到一款新产品，添加进看板

1. 用 Excel/Numbers/任何电子表格软件打开 `data/products.csv`
2. **追加一行**，按列填入：
   - `品类`：填 "洁面" / "面护" 等（**新品类直接写新名字**也会自动出现在筛选项）
   - `品牌`、`产品`、`规格`、`爆款香型`：照着已有的产品行的格式填
   - `天猫挂价`：可以是纯数字（如 `188`），也可以是富文本：`原价：¥168\n优惠后：¥80.11`
   - `天猫销量原始`、`抖音销量原始`：支持 `3万+` / `30万` / `6878` 等多种写法
   - `功效词`、`一句话卖点`、`小红书用户评价`：长文本即可
   - `包装图文件名`：见下面场景 B
3. 保存（**注意编码选 UTF-8**）
4. 浏览器右上 ⋯ → **Rerun**，看板就更新了

### 场景 B：给某个产品加包装图

1. 把图片（jpg/png）拷到 `data/images/` 目录
2. 推荐文件名格式：`{品类}_{产品名拼音/简短英文}.jpg`，例如 `洁面_jinzhanhua.jpg`
3. 在 CSV 该产品行的 `包装图文件名` 列填入这个文件名（**只填文件名，不带路径**）
4. 重启看板（或 Rerun），散点图鼠标悬停即可看到新图

### 场景 C：删除一个产品

直接在 CSV 里删那一行 → 保存 → Rerun。包装图文件可以一并删除（不删也不影响）。

### 场景 D：批量从 Excel 导入

如果你手头有原始的 `产品调研.xlsx`（含嵌入的包装图）：

```bash
# macOS
PRODUCT_XLSX="/path/to/你的.xlsx" python3 build_dataset.py

# Windows (PowerShell)
$env:PRODUCT_XLSX="C:\path\to\你的.xlsx"; python build_dataset.py
```

会重新生成 `data/products.csv` 与 `data/images/` 下的所有图片。**注意：会覆盖现有 CSV，操作前请备份。**

---

## 6️⃣ 看板里有什么

5 大 Tab：

| Tab | 主要回答 |
|---|---|
| 🏷 **市场全景** | 谁在卖什么价位卖多少？哪个价格带是销量主战场？市场上 70% 产品挤在哪个价格区间？ |
| 🧪 **产品力** | 哪条功效赛道最拥挤/最值钱？爆款产品都主推什么卖点？性价比 vs 销量呈什么关系？品牌如何定位？ |
| 🛒 **渠道策略** | 各品类、各品牌主要靠淘宝还是抖音？低价是不是更适合抖音？哪些功效在哪个渠道更好卖？ |
| 💬 **产品档案 × 用户口碑** | 选定产品对照其卖点和用户口碑、联合词云高亮"品牌想说"和"用户感受到"的共鸣词 |
| 📋 **明细数据** | 完整字段表格，可下载 CSV |

每张图右下角小灰字注明权重逻辑（数据口径），左上小灰字描述图本身要回答什么业务问题。

侧栏可按品类、品牌、价格采用（原价/优惠价）、销量口径（总/天猫/抖音）任意组合筛选；也可上传 CSV 临时预览（不影响公共数据）。

---

## 7️⃣ 常见问题排查

### Q: `python3` 命令找不到（Windows）
A: 用 `python` 替代。所有命令里把 `python3` 换成 `python`。

### Q: 启动后浏览器打不开
A: 手动打开 `http://localhost:8501`。如果还不行，看终端里有没有 `Address already in use`——说明 8501 端口被占用，加参数换个端口：
```bash
python3 -m streamlit run app.py --server.port 8502
```
然后访问 `http://localhost:8502`。

### Q: CSV 改了之后看板没更新
A: 浏览器右上角 **⋯ → Rerun**；或者把侧栏 "上传 CSV 临时预览" 上传一次再"恢复公共数据"。

### Q: 散点图悬停看不到包装图
A: 检查两点：① `data/images/` 里有没有那张图 ② CSV 的 "包装图文件名" 列填的是不是**正确文件名**（不带路径，含扩展名 `.jpg`/`.png`）

### Q: 词云里中文是方块
A: 看板会自动找系统字体。如果你在 Linux 上跑，需要装一下中文字体：
```bash
sudo apt-get install fonts-noto-cjk
```
Mac/Windows 默认字体已支持。

### Q: 报错 `ModuleNotFoundError: No module named 'xxx'`
A: 依赖没装齐，重跑：
```bash
python3 -m pip install -r requirements.txt
```

### Q: pip 装包很慢/超时
A: 国内可以用清华源加速：
```bash
python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 想改图表/想加新维度
A: 看板逻辑全在 `app.py` 这一个文件里，按 Tab 分块写得很清楚，照着已有的图复制改即可。要懂 [Plotly](https://plotly.com/python/) 与 [Streamlit](https://docs.streamlit.io)。

---

## 8️⃣ 项目目录结构

```
zy-Dashboard/
├── app.py                 # 看板主文件（所有图都在这里）
├── data_loader.py         # CSV 解析、价格/销量字段清洗、功效词归类
├── hover_image.py         # 散点图悬停弹包装图的 HTML+JS 组件
├── wc_render.py           # 词云生成（含权重叠加逻辑）
├── build_dataset.py       # 一次性脚本：从 xlsx 提取数据 → CSV+图片
├── image_extractor.py     # xlsx 中嵌入图片的提取工具
├── requirements.txt       # Python 依赖清单
├── packages.txt           # 部署到 Streamlit Cloud 时装的系统字体
├── .streamlit/config.toml # 看板主题、上传大小限制
├── README.md              # 本文档
└── data/
    ├── products.csv          # ★ 唯一数据源（你日常编辑这个）
    ├── products_template.csv # 空白模板（首行表头，给新人填）
    └── images/               # 所有包装图，按 品类_行号_hash.jpg 命名
```

---

## 9️⃣ 想分享给别人看（不希望对方装环境）

3 种方式：

**A. 部署到 Streamlit Community Cloud（免费、5 分钟）**
1. 把代码 push 到 GitHub（已是这一步的话跳过）
2. 打开 [share.streamlit.io](https://share.streamlit.io) → 用 GitHub 登录
3. New app → 选这个仓库 → Main file: `app.py` → Deploy
4. 几分钟后拿到 `https://xxx.streamlit.app` 公共 URL

**B. 自定义域名跳转**
- 有域名的话，在 DNS 里加 CNAME：`dashboard.你的域名.com` → `xxx.streamlit.app`

**C. 截图 / 录屏分享**
- 看板支持全屏 + 高清，直接 `Cmd+Shift+4`（Mac）截图，或 QuickTime 录屏

---

## 🔧 给开发者：扩展指南

- **加新图**：在 `app.py` 找到对应的 `with sections[N]:` 块，复制一个图块改 query/字段即可
- **改功效归类规则**：编辑 `data_loader.py` 顶部的 `EFFICACY_GROUPS` 字典
- **改词云配色**：编辑 `wc_render.py` 中 `colormap="plasma"` 等参数
- **加新筛选维度**：在 `app.py` 顶部的 `with st.sidebar:` 块加新 widget，下方 `mask = ...` 加对应过滤逻辑

技术栈：Python 3.10+ · [Streamlit](https://streamlit.io) · [Plotly](https://plotly.com/python/) · [pandas](https://pandas.pydata.org) · [jieba](https://github.com/fxsjy/jieba) · [wordcloud](https://github.com/amueller/word_cloud)

---

## 📮 联系/反馈

仓库地址：https://github.com/zzzkky-zy/zy-Dashboard

如果是数据贡献：直接修改 `data/products.csv` 提 PR，仓库管理员合并后所有人都能看到更新。
