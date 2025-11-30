"""
RAG 链模块
负责构建和执行 RAG 问答链
"""

from typing import List, Dict, Optional
import requests
import json
import os

from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
import time
import re
from difflib import SequenceMatcher


class RAGChain:
    """RAG 问答链"""
    
    def __init__(
        self,
        vector_store_manager,
        llm_provider: str = "ollama",
        model_name: str = "llama2",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        """
        初始化 RAG 链
        
        Args:
            vector_store_manager: 向量存储管理器
            llm_provider: LLM 提供商
            model_name: 模型名称
            base_url: API 基础 URL
            api_key: API 密钥
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        self.vector_store_manager = vector_store_manager
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 提示词模板
        self.prompt_template = """基于以下上下文信息回答问题。如果上下文中没有相关信息，请说"根据现有知识库，我无法回答这个问题"。

上下文信息：
{context}

问题：{question}

回答："""
    
    def _call_ollama(self, prompt: str) -> str:
        """调用 Ollama API"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        try:
            t = int(os.getenv("OLLAMA_TIMEOUT", "60"))
            response = requests.post(url, json=payload, timeout=t)
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
        
        except Exception as e:
            raise Exception(f"Ollama API 调用失败: {str(e)}")
    
    def _call_deepseek(self, prompt: str) -> str:
        """调用 DeepSeek API"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "你是一个专业的知识库助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            raise Exception(f"DeepSeek API 调用失败: {str(e)}")
    
    def _call_qwen(self, prompt: str) -> str:
        """调用通义千问 API"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "你是一个专业的知识库助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            raise Exception(f"通义千问 API 调用失败: {str(e)}")
    
    def _generate_response(self, prompt: str) -> str:
        """生成响应"""
        if self.llm_provider == "ollama":
            return self._call_ollama(prompt)
        elif self.llm_provider == "deepseek":
            return self._call_deepseek(prompt)
        elif self.llm_provider == "qwen":
            return self._call_qwen(prompt)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.llm_provider}")
    
    def query(self, question: str, top_k: int = 4) -> Dict:
        """
        执行 RAG 查询
        
        Args:
            question: 用户问题
            top_k: 检索的文档数量
            
        Returns:
            包含答案和来源的字典
        """
        try:
            # 1. 检索相关文档
            results = self.vector_store_manager.similarity_search(
                query=question,
                k=top_k
            )
            
            if not results:
                return {
                    'answer': '知识库中没有找到相关信息。',
                    'sources': [],
                    'error': None
                }
            
            # 2. 构建上下文
            context_parts = []
            sources = []
            
            for i, (doc, score) in enumerate(results, 1):
                context_parts.append(f"[文档 {i}]\n{doc.page_content}\n")
                sources.append({
                    'source': doc.metadata.get('source', 'unknown'),
                    'chunk_id': doc.metadata.get('chunk_id', 0),
                    'score': float(score),
                    'content': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content
                })
            
            context = "\n".join(context_parts)
            
            # 3. 构建提示词
            prompt = self.prompt_template.format(
                context=context,
                question=question
            )
            
            # 4. 生成答案（失败回退到检索来源提示）
            try:
                answer = self._generate_response(prompt)
            except Exception:
                answer = ""
            if not answer or not answer.strip():
                extractive = self._extractive_answer(context, question)
                if extractive.strip():
                    return {
                        'answer': extractive,
                        'sources': sources,
                        'error': None
                    }
                return {
                    'answer': '根据现有知识库，我无法回答这个问题',
                    'sources': sources,
                    'error': None
                }
            return {
                'answer': answer,
                'sources': sources,
                'error': None
            }
        
        except Exception as e:
            try:
                return {
                    'answer': '根据现有知识库，我无法回答这个问题',
                    'sources': [],
                    'error': None
                }
            except Exception:
                return {
                    'answer': '',
                    'sources': [],
                    'error': str(e)
                }

    def _extractive_answer(self, context: str, question: str) -> str:
        sentences = re.split(r"[\n。！？!?]+", context)
        def score(s):
            return SequenceMatcher(None, s, question).ratio()
        scored = [(s, score(s)) for s in sentences if s and s.strip()]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [s for s, _ in scored[:3]]
        return "\n".join(top).strip()

    def llm_health(self) -> Dict:
        start = time.time()
        provider = self.llm_provider
        model = self.model_name
        try:
            if provider == "ollama":
                import requests
                url = f"{self.base_url}/api/tags"
                r = requests.get(url, timeout=5)
                r.raise_for_status()
                data = r.json()
                names = []
                if isinstance(data, dict) and isinstance(data.get("models"), list):
                    names = [m.get("name") for m in data.get("models")]
                elif isinstance(data, list):
                    names = [m.get("name") for m in data]
                ok = model in names if names else True
                latency = (time.time() - start) * 1000
                return {"provider": provider, "model": model, "ok": ok, "message": None if ok else "模型未在 Ollama 中可用", "latency_ms": latency}
            elif provider in ("deepseek", "qwen"):
                import requests
                if not self.api_key:
                    latency = (time.time() - start) * 1000
                    return {"provider": provider, "model": model, "ok": False, "message": "缺少 API Key", "latency_ms": latency}
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"model": model, "messages": [{"role": "system", "content": "health"}, {"role": "user", "content": "ping"}], "max_tokens": 1, "temperature": 0}
                r = requests.post(url, headers=headers, json=payload, timeout=5)
                ok = r.status_code == 200
                msg = None if ok else f"HTTP {r.status_code}"
                latency = (time.time() - start) * 1000
                return {"provider": provider, "model": model, "ok": ok, "message": msg, "latency_ms": latency}
            else:
                latency = (time.time() - start) * 1000
                return {"provider": provider, "model": model, "ok": False, "message": "不支持的提供商", "latency_ms": latency}
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {"provider": provider, "model": model, "ok": False, "message": str(e), "latency_ms": latency}
