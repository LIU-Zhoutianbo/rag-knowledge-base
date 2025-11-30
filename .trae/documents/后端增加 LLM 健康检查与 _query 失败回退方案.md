## 目标
- 在后端新增 `GET /llm/health` 用于检测当前 LLM 提供商/模型的可用性。
- 在 `/query` 内，当 LLM 不可用或调用失败时，返回“根据现有知识库，我无法回答这个问题”并附带检索到的来源，而不是直接报错。

## 技术方案
### 新增 LLM 健康检查
- 路由：在 `backend/main.py` 增加 `@app.get("/llm/health")`。
- 返回模型：新增 `LLMHealthResponse`（`provider`, `model`, `ok`, `message`, `latency_ms`）。文件：`backend/models/response_models.py`。
- 核心实现：在 `src/rag_chain.py` 增加 `def llm_health(self) -> dict`：
  - `ollama`：`GET {base_url}/api/tags`（timeout 5s），校验是否存在 `model_name`，记录耗时；若网络错误或无该模型，`ok=False` 并给出原因。
  - `deepseek`/`qwen`：若缺少 `api_key` 则直接 `ok=False`。否则发送一次最小化 `chat/completions`（max_tokens=1，timeout 5s），200 即 `ok=True`，其余 `ok=False` 并返回服务端消息。
- 设计原则：只做“连通性与基本就绪”探测，避免产生高成本调用；所有请求用短超时，返回明确的错误信息。

### /query 失败回退
- 修改 `src/rag_chain.py:query()`：
  - 先执行相似度检索（已有逻辑）。
  - 尝试生成答案；若抛错或返回空字符串：
    - 若有检索结果：返回固定文案“根据现有知识库，我无法回答这个问题”，并附带来源列表；`error=None`（不作为错误处理）。
    - 若无检索结果：返回“知识库中没有找到相关信息。”（保留现逻辑）。
- 这样前端不会显示“后端不可用或请求失败”，而是拿到可用的检索来源和可读提示。

## 具体改动位置
- `backend/main.py`：新增 `@app.get('/llm/health')`，调用 `rag_pipeline.rag_chain.llm_health()` 并返回。
- `backend/models/response_models.py`：新增 `class LLMHealthResponse(BaseModel)`。
- `src/rag_chain.py`：
  - 新增 `llm_health()` 方法；
  - 在 `query()` 中加入 LLM 失败时的回退分支。

## 验证与自检
- 后端启动后：
  - 访问 `GET /llm/health`：
    - 未启动 Ollama 或未拉取模型：返回 `ok=false` 和原因；
    - 启动并拉取模型：返回 `ok=true`，包含耗时与模型名。
  - 上传文档后，停止 LLM 服务，调用 `POST /query`：返回固定中文提示与检索来源（非错误）。
- 边界：无 API Key 的在线提供商应清晰返回 `ok=false` 和缺失密钥提示。

## 可选前端增强（如你需要）
- 侧边栏显示 LLM 健康状态（调用 `/llm/health`），在 `ok=false` 时提示“模型不可用”，但仍允许发送以展示基于检索的回退答复。

## 影响评估
- 无新增外部依赖；仅增加一个后端路由与若干方法。
- 与现有 API 向后兼容；前端无需同步改动即可受益于 `/query` 的回退行为。