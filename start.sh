#!/bin/bash
# 启动产品调研看板
# 用法: bash /Users/yaman/product_dashboard/start.sh
set -e
cd "$(dirname "$0")"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
exec streamlit run app.py --server.headless true --server.port 8501 --server.fileWatcherType auto
