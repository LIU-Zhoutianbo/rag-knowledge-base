from src.rag_chain import RAGChain
from src.vector_store_manager import VectorStoreManager
from src.chat_history_manager import ChatHistoryManager
import os
import yaml
from langchain.schema import Document
from typing import Optional
from src.document_processor import DocumentProcessor

class RAGPipeline:
    def __init__(self):
        # 加载配置
        with open(os.path.join(os.getcwd(), "config.yaml"), "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        vs_cfg = cfg.get("vector_store", {})
        emb_cfg = cfg.get("embeddings", {})
        llm_cfg = cfg.get("llm", {})
        retrieval_cfg = cfg.get("retrieval", {})
        doc_cfg = cfg.get("document", {})

        # 初始化向量存储（与前端保持一致）
        self.vector_store_manager = VectorStoreManager(
            persist_directory=vs_cfg.get("persist_directory", "./vector_store"),
            collection_name=vs_cfg.get("collection_name", "knowledge_base"),
            embedding_model=emb_cfg.get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            device=emb_cfg.get("device", "cpu")
        )
        self.chat_history_manager = ChatHistoryManager()
        self.top_k = retrieval_cfg.get("top_k", 4)
        self.document_processor = DocumentProcessor(
            chunk_size=doc_cfg.get("chunk_size", 1000),
            chunk_overlap=doc_cfg.get("chunk_overlap", 200)
        )

        # 初始化 LLM（按配置）
        default_provider = llm_cfg.get("default_provider", "ollama")
        default_model = llm_cfg.get("default_model", "llama2")
        provider_base = {
            "ollama": os.getenv("OLLAMA_BASE_URL", llm_cfg.get("providers", {}).get("ollama", {}).get("base_url", "http://localhost:11434")),
            "deepseek": os.getenv("DEEPSEEK_BASE_URL", llm_cfg.get("providers", {}).get("deepseek", {}).get("base_url", "https://api.deepseek.com")),
            "qwen": os.getenv("QWEN_BASE_URL", llm_cfg.get("providers", {}).get("qwen", {}).get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")),
        }
        api_key = None
        if default_provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
        elif default_provider == "qwen":
            api_key = os.getenv("QWEN_API_KEY")

        self.rag_chain = RAGChain(
            vector_store_manager=self.vector_store_manager,
            llm_provider=default_provider,
            model_name=default_model,
            base_url=provider_base.get(default_provider),
            api_key=api_key,
            temperature=llm_cfg.get("temperature", 0.3),
            max_tokens=llm_cfg.get("max_tokens", 2000)
        )

    def query(self, question: str, session_id=None, override_llm: Optional[dict] = None):
        if session_id is None:
            session_id = "default"
        self.chat_history_manager.add_message(session_id, "user", question)
        chain = self.rag_chain
        if override_llm:
            chain = RAGChain(
                vector_store_manager=self.vector_store_manager,
                llm_provider=override_llm.get("llm_provider", self.rag_chain.llm_provider),
                model_name=override_llm.get("model_name", self.rag_chain.model_name),
                base_url=override_llm.get("base_url", self.rag_chain.base_url),
                api_key=override_llm.get("api_key", self.rag_chain.api_key),
                temperature=self.rag_chain.temperature,
                max_tokens=self.rag_chain.max_tokens
            )
        result = chain.query(question, top_k=self.top_k)
        self.chat_history_manager.add_message(session_id, "assistant", result["answer"], result.get("sources"))
        return result["answer"], result.get("sources", [])

    def collection_info(self) -> dict:
        return self.vector_store_manager.get_collection_info()

    def clear_collection(self):
        self.vector_store_manager.delete_collection()
        self.vector_store_manager = VectorStoreManager(
            persist_directory=self.vector_store_manager.persist_directory,
            collection_name=self.vector_store_manager.collection_name,
            embedding_model=self.vector_store_manager.embeddings.model_name if hasattr(self.vector_store_manager.embeddings, 'model_name') else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.rag_chain = RAGChain(
            vector_store_manager=self.vector_store_manager,
            llm_provider=self.rag_chain.llm_provider,
            model_name=self.rag_chain.model_name,
            base_url=self.rag_chain.base_url,
            api_key=self.rag_chain.api_key,
            temperature=self.rag_chain.temperature,
            max_tokens=self.rag_chain.max_tokens
        )

    def ingest_documents(self, docs: list[dict]) -> list[str]:
        lc_docs = []
        for d in docs:
            meta = d.get("metadata") or {}
            if d.get("source"):
                meta["source"] = d["source"]
            lc_docs.append(Document(page_content=d["content"], metadata=meta))
        ids = self.vector_store_manager.add_documents(lc_docs)
        return ids

    def ingest_files(self, file_paths: list[str]) -> list[str]:
        all_docs = []
        for p in file_paths:
            docs = self.document_processor.process_document(p)
            all_docs.extend(docs)
        ids = self.vector_store_manager.add_documents(all_docs)
        return ids
