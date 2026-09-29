# -*- coding: utf-8 -*-
"""元数据模板：复制到项目 <OUT>/papers.py 并按实际情况修改。

PAPERS 每项 = (文件名前缀, 序号, 年份, 英文标题)
  * 文件名前缀：BASE 目录下以该字符串开头的唯一 PDF 文件名。
  * 序号：最终排序编号（按发表年份从小到大，两位）。
  * 年份：以真实发表年为准（arXiv 预印本用其年份）。
"""
import os

BASE = r'E:\path\to\pdfs'                       # PDF 所在文件夹
OUT = os.path.join(BASE, 'translation')         # 全部中间产物输出目录

# 合集标题（渲染封面/书脊用）
COLLECTION_TITLE = '某某主题相关文献中英对照集'
COLLECTION_TITLE_EN = 'A Bilingual Collection of Key Papers'
COLLECTION_SUBTITLE = '中英逐段对照 · 术语注释版'

PAPERS = [
    # ("01_2007_", 1, 2007, "Influence of photon angular momentum on ..."),
    # ("02_2008_", 2, 2008, "..."),
]


def find_pdf(prefix):
    for f in os.listdir(BASE):
        if f.startswith(prefix) and f.lower().endswith('.pdf'):
            return os.path.join(BASE, f)
    raise FileNotFoundError(prefix)
