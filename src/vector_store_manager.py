"""
向量存储管理模块
负责向量数据库的创建、更新和检索
"""

from typing import List, Optional
from pathlib import Path

from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(
        self,
        persist_directory: str = "./vector_store",
        collection_name: str = "knowledge_base",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device: str = "cpu",

    ):
        """
        初始化向量存储管理器
        
        Args:
            persist_directory: 持久化目录
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # 创建目录
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # 初始化嵌入模型
        print(f"正在加载嵌入模型: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True, 'batch_size': 64},
        )
        
        # 初始化或加载向量存储
        self.vector_store = self._load_or_create_vector_store()
    
    def _load_or_create_vector_store(self) -> Chroma:
        """加载或创建向量存储"""
        try:
            # 尝试加载现有的向量存储
            vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            print(f"已加载现有向量存储，文档数量: {vector_store._collection.count()}")
            return vector_store
        
        except Exception as e:
            print(f"创建新的向量存储: {str(e)}")
            return Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表
            
        Returns:
            文档 ID 列表
        """
        try:
            ids = self.vector_store.add_documents(documents)
            self.vector_store.persist()
            print(f"成功添加 {len(documents)} 个文档块")
            return ids
        
        except Exception as e:
            raise Exception(f"添加文档失败: {str(e)}")
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        score_threshold: Optional[float] = None
    ) -> List[tuple[Document, float]]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            score_threshold: 相似度阈值
            
        Returns:
            (文档, 相似度分数) 列表
        """
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k
            )
            
            # 过滤低于阈值的结果
            if score_threshold is not None:
                results = [(doc, score) for doc, score in results if score >= score_threshold]
            
            return results
        
        except Exception as e:
            raise Exception(f"搜索失败: {str(e)}")
    
    def get_retriever(self, search_kwargs: dict = None):
        """
        获取检索器
        
        Args:
            search_kwargs: 搜索参数
            
        Returns:
            检索器对象
        """
        if search_kwargs is None:
            search_kwargs = {"k": 4}
        
        return self.vector_store.as_retriever(
            search_kwargs=search_kwargs
        )
    
    def delete_collection(self):
        """删除集合"""
        try:
            self.vector_store.delete_collection()
            print(f"已删除集合: {self.collection_name}")
        except Exception as e:
            raise Exception(f"删除集合失败: {str(e)}")
    
    def get_collection_info(self) -> dict:
        """获取集合信息"""
        try:
            count = 0
            try:
                count = self.vector_store._collection.count()
            except Exception:
                count = self.vector_store.collection.count() if hasattr(self.vector_store, 'collection') else 0
            return {
                'collection_name': self.collection_name,
                'document_count': count,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            return {
                'collection_name': self.collection_name,
                'document_count': 0,
                'persist_directory': self.persist_directory,
                'error': str(e)
            }
