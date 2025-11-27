"""
RAG 知识库问答系统 - Streamlit 应用
"""

import streamlit as st
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv
import time

from src.document_processor import DocumentProcessor
from src.vector_store_manager import VectorStoreManager
from src.rag_chain import RAGChain

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="RAG 知识库问答系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .source-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .score-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def load_config():
    """加载配置文件"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def initialize_session_state():
    """初始化会话状态"""
    if 'config' not in st.session_state:
        st.session_state.config = load_config()
    
    if 'document_processor' not in st.session_state:
        config = st.session_state.config
        st.session_state.document_processor = DocumentProcessor(
            chunk_size=config['document']['chunk_size'],
            chunk_overlap=config['document']['chunk_overlap']
        )
    
    if 'vector_store_manager' not in st.session_state:
        config = st.session_state.config
        st.session_state.vector_store_manager = VectorStoreManager(
            persist_directory=config['vector_store']['persist_directory'],
            collection_name=config['vector_store']['collection_name'],
            embedding_model=config['embeddings']['model_name']
        )
    
    if 'rag_chain' not in st.session_state:
        st.session_state.rag_chain = None
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("### ⚙️ 系统设置")
        
        # LLM 配置
        with st.expander("🤖 LLM 配置", expanded=True):
            llm_provider = st.selectbox(
                "选择 LLM 提供商",
                ["ollama", "deepseek", "qwen"],
                format_func=lambda x: {
                    "ollama": "Ollama (本地免费)",
                    "deepseek": "DeepSeek (在线，便宜)",
                    "qwen": "通义千问 (在线)"
                }[x]
            )
            
            config = st.session_state.config
            
            if llm_provider == "ollama":
                base_url = st.text_input(
                    "Ollama URL",
                    value=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
                )
                models = [m['name'] for m in config['llm']['providers']['ollama']['models']]
                model_name = st.selectbox("选择模型", models)
                api_key = None
            
            elif llm_provider == "deepseek":
                base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
                api_key = st.text_input(
                    "DeepSeek API Key",
                    value=os.getenv('DEEPSEEK_API_KEY', ''),
                    type="password"
                )
                models = [m['name'] for m in config['llm']['providers']['deepseek']['models']]
                model_name = st.selectbox("选择模型", models)
            
            else:  # qwen
                base_url = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
                api_key = st.text_input(
                    "Qwen API Key",
                    value=os.getenv('QWEN_API_KEY', ''),
                    type="password"
                )
                models = [m['name'] for m in config['llm']['providers']['qwen']['models']]
                model_name = st.selectbox("选择模型", models)
            
            temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
            max_tokens = st.slider("Max Tokens", 500, 4000, 2000, 100)
            
            if st.button("🚀 初始化 RAG 系统", use_container_width=True):
                try:
                    with st.spinner("正在初始化 RAG 系统..."):
                        st.session_state.rag_chain = RAGChain(
                            vector_store_manager=st.session_state.vector_store_manager,
                            llm_provider=llm_provider,
                            model_name=model_name,
                            base_url=base_url,
                            api_key=api_key,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    st.success("✅ RAG 系统初始化成功！")
                except Exception as e:
                    st.error(f"❌ 初始化失败: {str(e)}")
        
        # 文档管理
        st.markdown("---")
        st.markdown("### 📁 文档管理")
        
        uploaded_files = st.file_uploader(
            "上传文档",
            type=['pdf', 'txt', 'md', 'docx'],
            accept_multiple_files=True
        )
        
        if uploaded_files and st.button("📤 处理并添加文档", use_container_width=True):
            process_documents(uploaded_files)
        
        # 知识库信息
        st.markdown("---")
        st.markdown("### 📊 知识库信息")
        
        info = st.session_state.vector_store_manager.get_collection_info()
        st.metric("文档块数量", info['document_count'])
        
        if st.button("🗑️ 清空知识库", use_container_width=True):
            try:
                st.session_state.vector_store_manager.delete_collection()
                st.session_state.vector_store_manager = VectorStoreManager(
                    persist_directory=st.session_state.config['vector_store']['persist_directory'],
                    collection_name=st.session_state.config['vector_store']['collection_name'],
                    embedding_model=st.session_state.config['embeddings']['model_name']
                )
                st.success("✅ 知识库已清空")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 清空失败: {str(e)}")


def process_documents(uploaded_files):
    """处理上传的文档"""
    try:
        with st.spinner("正在处理文档..."):
            # 创建临时目录
            temp_dir = Path("./temp_uploads")
            temp_dir.mkdir(exist_ok=True)
            
            all_documents = []
            
            for uploaded_file in uploaded_files:
                # 保存文件
                file_path = temp_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 处理文档
                documents = st.session_state.document_processor.process_document(str(file_path))
                all_documents.extend(documents)
                
                # 删除临时文件
                file_path.unlink()
            
            # 添加到向量存储
            st.session_state.vector_store_manager.add_documents(all_documents)
            
            # 获取文档信息
            info = st.session_state.document_processor.get_document_info(all_documents)
            
            st.markdown(f"""
            <div class="success-box">
                <strong>✅ 文档处理成功！</strong><br>
                • 文档数量: {len(uploaded_files)}<br>
                • 切分块数: {info['total_chunks']}<br>
                • 总字符数: {info['total_characters']:,}<br>
                • 平均块大小: {info['avg_chunk_size']} 字符
            </div>
            """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"❌ 处理文档失败: {str(e)}")


def render_chat_interface():
    """渲染聊天界面"""
    st.markdown('<div class="main-header">📚 RAG 知识库问答系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">基于检索增强生成的智能问答系统</div>', unsafe_allow_html=True)
    
    # 检查 RAG 系统是否初始化
    if st.session_state.rag_chain is None:
        st.markdown("""
        <div class="info-box">
            <strong>ℹ️ 使用说明</strong><br>
            1. 在侧边栏选择 LLM 提供商并初始化 RAG 系统<br>
            2. 上传文档到知识库<br>
            3. 开始提问！
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 检查知识库是否为空
    info = st.session_state.vector_store_manager.get_collection_info()
    if info['document_count'] == 0:
        st.warning("⚠️ 知识库为空，请先上传文档")
        return
    
    # 显示对话历史
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            with st.chat_message("user"):
                st.write(msg['content'])
        else:
            with st.chat_message("assistant"):
                st.write(msg['answer'])
                
                if msg.get('sources'):
                    with st.expander("📖 查看来源"):
                        for i, source in enumerate(msg['sources'], 1):
                            st.markdown(f"""
                            <div class="source-card">
                                <strong>来源 {i}:</strong> {source['source']} 
                                <span class="score-badge">相似度: {source['score']:.2f}</span><br>
                                <em>{source['content']}</em>
                            </div>
                            """, unsafe_allow_html=True)
    
    # 输入区域
    user_question = st.chat_input("输入您的问题...")
    
    if user_question:
        # 添加用户消息
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_question
        })
        
        # 显示用户消息
        with st.chat_message("user"):
            st.write(user_question)
        
        # 生成回答
        with st.chat_message("assistant"):
            with st.spinner("🤔 思考中..."):
                start_time = time.time()
                result = st.session_state.rag_chain.query(user_question)
                end_time = time.time()
                
                if result['error']:
                    st.error(f"❌ 生成回答失败: {result['error']}")
                else:
                    st.write(result['answer'])
                    
                    if result['sources']:
                        with st.expander("📖 查看来源"):
                            for i, source in enumerate(result['sources'], 1):
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong>来源 {i}:</strong> {source['source']} 
                                    <span class="score-badge">相似度: {source['score']:.2f}</span><br>
                                    <em>{source['content']}</em>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    st.caption(f"⏱️ 响应时间: {end_time - start_time:.2f} 秒")
                    
                    # 添加到历史
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'answer': result['answer'],
                        'sources': result['sources']
                    })


def main():
    """主函数"""
    initialize_session_state()
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()