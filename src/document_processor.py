"""
文档处理模块
负责文档加载、切分和向量化
"""

import os
from typing import List
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from langchain.schema import Document


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化文档处理器
        
        Args:
            chunk_size: 文档切分的块大小
            chunk_overlap: 块之间的重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        加载文档
        
        Args:
            file_path: 文档路径
            
        Returns:
            文档列表
        """
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == '.pdf':
                loader = PyPDFLoader(file_path)
            elif file_extension == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_extension == '.md':
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_extension == '.docx':
                loader = Docx2txtLoader(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_extension}")
            
            documents = loader.load()
            
            # 添加文件名到元数据
            for doc in documents:
                doc.metadata['source'] = os.path.basename(file_path)
            
            return documents
        
        except Exception as e:
            raise Exception(f"加载文档失败: {str(e)}")
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        切分文档
        
        Args:
            documents: 文档列表
            
        Returns:
            切分后的文档列表
        """
        try:
            split_docs = self.text_splitter.split_documents(documents)
            
            # 为每个切分添加索引
            for i, doc in enumerate(split_docs):
                doc.metadata['chunk_id'] = i
            
            return split_docs
        
        except Exception as e:
            raise Exception(f"切分文档失败: {str(e)}")
    
    def process_document(self, file_path: str) -> List[Document]:
        """
        处理文档（加载 + 切分）
        
        Args:
            file_path: 文档路径
            
        Returns:
            处理后的文档列表
        """
        documents = self.load_document(file_path)
        split_docs = self.split_documents(documents)
        return split_docs
    
    def get_document_info(self, documents: List[Document]) -> dict:
        """
        获取文档信息
        
        Args:
            documents: 文档列表
            
        Returns:
            文档信息字典
        """
        total_chars = sum(len(doc.page_content) for doc in documents)
        sources = set(doc.metadata.get('source', 'unknown') for doc in documents)
        
        return {
            'total_chunks': len(documents),
            'total_characters': total_chars,
            'sources': list(sources),
            'avg_chunk_size': total_chars // len(documents) if documents else 0
        }