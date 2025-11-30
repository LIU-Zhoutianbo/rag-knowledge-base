from fastapi import FastAPI
from fastapi import Body, UploadFile, File
from typing import List
from backend.rag_pipeline import RAGPipeline
from backend.models.request_models import QueryRequest, IngestDocumentsRequest
from backend.models.response_models import QueryResponse, IngestResponse, CollectionInfoResponse, LLMHealthResponse, TaskStatusResponse
import uuid
import threading
from pathlib import Path
import os

app = FastAPI(title="RAG Knowledge Base API")
rag_pipeline = RAGPipeline()  # 封装初始化逻辑，加载 vector store + LLM

@app.post("/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    try:
        override = None
        if any([req.llm_provider, req.model_name, req.base_url, req.api_key]):
            override = {
                "llm_provider": req.llm_provider,
                "model_name": req.model_name,
                "base_url": req.base_url,
                "api_key": req.api_key,
            }
        answer, sources = rag_pipeline.query(req.question, session_id=req.session_id, override_llm=override)
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        return QueryResponse(answer="", sources=[], error=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/llm/health", response_model=LLMHealthResponse)
def llm_health():
    try:
        res = rag_pipeline.rag_chain.llm_health()
        return LLMHealthResponse(**res)
    except Exception as e:
        return LLMHealthResponse(
            provider=rag_pipeline.rag_chain.llm_provider,
            model=rag_pipeline.rag_chain.model_name,
            ok=False,
            message=str(e),
            latency_ms=0.0
        )

@app.get("/vector-store/info", response_model=CollectionInfoResponse)
def vector_store_info():
    info = rag_pipeline.collection_info()
    return CollectionInfoResponse(**info)

@app.delete("/vector-store/collection")
def clear_vector_store():
    try:
        rag_pipeline.clear_collection()
        return {"status": "cleared"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/vector-store/documents", response_model=IngestResponse)
def ingest_documents(req: IngestDocumentsRequest):
    try:
        ids = rag_pipeline.ingest_documents([d.dict() for d in req.documents])
        return IngestResponse(inserted=len(ids), ids=ids)
    except Exception as e:
        return IngestResponse(inserted=0, ids=[], error=str(e))

@app.post("/vector-store/upload", response_model=IngestResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    try:
        import os
        from pathlib import Path
        temp_dir = Path("./temp_uploads_backend")
        temp_dir.mkdir(exist_ok=True)
        saved_paths = []
        for f in files:
            content = await f.read()
            save_path = temp_dir / f.filename
            with open(save_path, "wb") as out:
                out.write(content)
            saved_paths.append(str(save_path))
        ids = rag_pipeline.ingest_files(saved_paths)
        for p in saved_paths:
            try:
                os.remove(p)
            except Exception:
                pass
        return IngestResponse(inserted=len(ids), ids=ids)
    except Exception as e:
        return IngestResponse(inserted=0, ids=[], error=str(e))

TASKS = {}
TASKS_LOCK = threading.Lock()

@app.post("/vector-store/upload_async")
async def upload_documents_async(files: List[UploadFile] = File(...)):
    temp_dir = Path("./temp_uploads_backend")
    temp_dir.mkdir(exist_ok=True)
    saved_paths = []
    for f in files:
        content = await f.read()
        save_path = temp_dir / f.filename
        with open(save_path, "wb") as out:
            out.write(content)
        saved_paths.append(str(save_path))
    task_id = str(uuid.uuid4())
    with TASKS_LOCK:
        TASKS[task_id] = {
            "status": "running",
            "inserted": 0,
            "error": None,
            "processed_files": 0,
            "total_files": len(saved_paths)
        }
    def worker(paths, tid):
        try:
            inserted_total = 0
            for idx, p in enumerate(paths, 1):
                ids = rag_pipeline.ingest_files([p])
                inserted_total += len(ids)
                with TASKS_LOCK:
                    TASKS[tid]["processed_files"] = idx
                    TASKS[tid]["inserted"] = inserted_total
            for p in paths:
                try:
                    os.remove(p)
                except Exception:
                    pass
            with TASKS_LOCK:
                TASKS[tid]["status"] = "done"
        except Exception as e:
            with TASKS_LOCK:
                TASKS[tid]["status"] = "error"
                TASKS[tid]["error"] = str(e)
    threading.Thread(target=worker, args=(saved_paths, task_id), daemon=True).start()
    return {"task_id": task_id}

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    with TASKS_LOCK:
        t = TASKS.get(task_id)
    if not t:
        return TaskStatusResponse(task_id=task_id, status="not_found", inserted=0, error="task not found", processed_files=0, total_files=0)
    return TaskStatusResponse(task_id=task_id, status=t["status"], inserted=t["inserted"], error=t["error"], processed_files=t["processed_files"], total_files=t["total_files"])
