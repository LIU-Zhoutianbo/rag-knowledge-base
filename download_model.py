#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 27/11/2025 13:39
@Author  : leochoutianbo@gmail.com
@File    : download_model.py.py
"""
# download_multilingual_model.py
from sentence_transformers import SentenceTransformer
import os

# 创建模型目录
os.makedirs("./models", exist_ok=True)

print("开始下载多语言模型...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2',
                           cache_folder='./models')
print("多语言模型下载完成！")

# 测试中文支持
texts = ["这是一个测试文档", "This is a test document"]
embeddings = model.encode(texts)
print(f"嵌入维度: {embeddings.shape}")