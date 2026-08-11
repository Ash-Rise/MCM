# -*- coding: utf-8 -*-
from docx import Document

doc = Document(r"D:\大二上学习资料\数模国赛\模板资料\format2024.docx")
for p in doc.paragraphs:
    t = p.text.strip()
    if "摘要" in t or "英文" in t or "关键词" in t:
        print(t)
