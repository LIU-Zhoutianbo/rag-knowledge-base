# RAG 知识库问答系统

一个基于检索增强生成（RAG）技术的智能问答系统，支持本地运行，解决 LLM 幻觉问题。

## ✨ 特性

- 📚 **文档上传**：支持 PDF、TXT、MD、DOCX 格式
- 🔍 **智能检索**：基于向量相似度的语义搜索
- 💬 **精准问答**：基于文档内容生成准确答案
- 📖 **来源追溯**：显示答案来源和相似度分数
- 💻 **本地运行**：支持 Ollama 本地模型（完全免费）
- 🌐 **在线模型**：支持 DeepSeek、通义千问（价格便宜）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置（可选）

如果使用在线模型，复制 `.env.example` 为 `.env` 并填入 API Key：

```bash
cp .env.example .env
```

### 3. 启动 Ollama（如果使用本地模型）

```bash
# 安装 Ollama: https://ollama.ai/
ollama pull llama2
# 或者
ollama pull mistral
```

### 4. 运行应用

```bash
streamlit run app.py
```

访问 http://localhost:8501

## 📖 使用说明

### 步骤 1：初始化 RAG 系统

1. 在侧边栏选择 LLM 提供商：
   - **Ollama**（推荐新手）：本地免费，需要先安装 Ollama
   - **DeepSeek**：在线，价格最便宜（¥0.001/1K tokens）
   - **通义千问**：在线，阿里云

2. 如果使用在线模型，输入 API Key

3. 点击"初始化 RAG 系统"

### 步骤 2：上传文档

1. 点击"上传文档"按钮
2. 选择一个或多个文档（PDF、TXT、MD、DOCX）
3. 点击"处理并添加文档"
4. 等待文档处理完成

### 步骤 3：开始提问

1. 在输入框输入问题
2. 系统会自动检索相关文档
3. 基于文档内容生成答案
4. 点击"查看来源"可以看到答案的出处

## 🛠️ 技术架构

```
用户问题
    ↓
文档检索（向量相似度搜索）
    ↓
上下文构建（Top-K 相关文档）
    ↓
LLM 生成答案（基于上下文）
    ↓
返回答案 + 来源
```

### 核心组件

1. **文档处理器**（`document_processor.py`）
   - 加载多种格式文档
   - 智能切分文档（RecursiveCharacterTextSplitter）
   - 保留文档元数据

2. **向量存储管理器**（`vector_store_manager.py`）
   - ChromaDB 向量数据库
   - Sentence Transformers 嵌入模型
   - 持久化存储

3. **RAG 链**（`rag_chain.py`）
   - 检索相关文档
   - 构建上下文
   - 调用 LLM 生成答案

## 📊 模型对比

| 模型 | 类型 | 价格 | 优点 | 缺点 |
|------|------|------|------|------|
| Ollama (Llama 2) | 本地 | 免费 | 完全免费，隐私好 | 需要本地安装，速度较慢 |
| Ollama (Mistral) | 本地 | 免费 | 完全免费，质量好 | 需要本地安装 |
| DeepSeek Chat | 在线 | ¥0.001/1K | 超便宜，质量好 | 需要网络 |
| 通义千问 Turbo | 在线 | ¥0.002/1K | 快速，中文好 | 需要网络 |

## 🔧 配置说明

### 文档处理配置

```yaml
document:
  chunk_size: 1000        # 文档切分大小
  chunk_overlap: 200      # 切分重叠大小
  max_file_size_mb: 50    # 最大文件大小
```

### 嵌入模型配置

```yaml
embeddings:
  model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  # 多语言支持，中英文都很好
```

### 检索配置

```yaml
retrieval:
  top_k: 4                # 检索文档数量
  score_threshold: 0.5    # 相似度阈值
```

## 💡 使用技巧

### 1. 如何提高答案质量？

- **上传高质量文档**：文档内容越准确，答案越好
- **增加 top_k 值**：检索更多相关文档
- **降低 temperature**：让答案更确定（0.1-0.3）
- **使用更好的模型**：如 DeepSeek、Qwen Max

### 2. 如何处理大文档？

- **调整 chunk_size**：大文档可以增大到 1500-2000
- **增加 chunk_overlap**：保证上下文连贯性（300-400）
- **分批上传**：避免一次性处理太多文档

### 3. 如何优化检索效果？

- **使用更好的嵌入模型**：
  - 中文：`BAAI/bge-small-zh-v1.5`
  - 英文：`sentence-transformers/all-MiniLM-L6-v2`
- **调整 score_threshold**：过滤不相关的结果
- **增加 top_k**：检索更多候选文档

## 🐛 常见问题

### 1. Ollama 连接失败？

```bash
# 检查 Ollama 是否运行
ollama list

# 启动 Ollama 服务
ollama serve
```

### 2. 嵌入模型下载慢？

使用国内镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. 内存不足？

- 减少 `chunk_size` 和 `top_k`
- 使用更小的嵌入模型
- 分批处理文档

### 4. 答案不准确？

- 检查文档是否包含相关信息
- 增加 `top_k` 值
- 降低 `temperature`
- 查看"来源"确认检索是否正确

## 📁 项目结构

```
rag-knowledge-base/
├── app.py                    # 主应用
├── requirements.txt          # 依赖
├── config.yaml              # 配置文件
├── .env.example             # 环境变量示例
├── src/
│   ├── document_processor.py      # 文档处理
│   ├── vector_store_manager.py    # 向量存储
│   └── rag_chain.py              # RAG 链
├── vector_store/            # 向量数据库（自动生成）
├── temp_uploads/            # 临时文件（自动生成）
└── README.md               # 说明文档
```

## 🎯 应用场景

- **企业知识库**：公司文档、政策、流程问答
- **技术文档助手**：API 文档、技术手册查询
- **学习助手**：课程资料、笔记问答
- **法律咨询**：法律文件、合同条款查询
- **医疗助手**：医学文献、病例分析

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**注意**：本项目专注于 RAG 技术实现，提供完整的本地运行方案，适合学习和企业应用。