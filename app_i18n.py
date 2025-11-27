"""
RAG 知识库问答系统 - 多语言版本
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
from src.i18n import I18n

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="RAG Knowledge Base Q&A",
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
    if 'i18n' not in st.session_state:
        st.session_state.i18n = I18n(default_language="zh_TW")
    
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
    i18n = st.session_state.i18n
    
    with st.sidebar:
        # 语言选择
        st.markdown(f"### {i18n('sidebar.language_settings')}")
        available_languages = i18n.get_available_languages()
        current_lang_name = available_languages.get(i18n.current_language, "繁體中文")
        
        selected_lang = st.selectbox(
            i18n('sidebar.select_language'),
            options=list(available_languages.keys()),
            format_func=lambda x: available_languages[x],
            index=list(available_languages.keys()).index(i18n.current_language),
            key="language_selector"
        )
        
        if selected_lang != i18n.current_language:
            i18n.set_language(selected_lang)
            st.rerun()
        
        st.markdown("---")
        st.markdown(f"### {i18n('sidebar.settings')}")
        
        # LLM 配置
        with st.expander(i18n('sidebar.llm_config'), expanded=True):
            llm_provider = st.selectbox(
                i18n('sidebar.select_provider'),
                ["ollama", "deepseek", "qwen"],
                format_func=lambda x: i18n(f'providers.{x}')
            )
            
            config = st.session_state.config
            
            if llm_provider == "ollama":
                base_url = st.text_input(
                    i18n('sidebar.ollama_url'),
                    value=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
                )
                models = [m['name'] for m in config['llm']['providers']['ollama']['models']]
                model_name = st.selectbox(i18n('sidebar.select_model'), models)
                api_key = None
            
            elif llm_provider == "deepseek":
                base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
                api_key = st.text_input(
                    i18n('sidebar.api_key'),
                    value=os.getenv('DEEPSEEK_API_KEY', ''),
                    type="password"
                )
                models = [m['name'] for m in config['llm']['providers']['deepseek']['models']]
                model_name = st.selectbox(i18n('sidebar.select_model'), models)
            
            else:  # qwen
                base_url = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
                api_key = st.text_input(
                    i18n('sidebar.api_key'),
                    value=os.getenv('QWEN_API_KEY', ''),
                    type="password"
                )
                models = [m['name'] for m in config['llm']['providers']['qwen']['models']]
                model_name = st.selectbox(i18n('sidebar.select_model'), models)
            
            temperature = st.slider(i18n('sidebar.temperature'), 0.0, 1.0, 0.3, 0.1)
            max_tokens = st.slider(i18n('sidebar.max_tokens'), 500, 4000, 2000, 100)
            
            if st.button(i18n('sidebar.initialize_rag'), use_container_width=True):
                try:
                    with st.spinner(i18n('messages.processing_documents')):
                        st.session_state.rag_chain = RAGChain(
                            vector_store_manager=st.session_state.vector_store_manager,
                            llm_provider=llm_provider,
                            model_name=model_name,
                            base_url=base_url,
                            api_key=api_key,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    st.success(i18n('messages.rag_initialized'))
                except Exception as e:
                    st.error(f"{i18n('messages.initialization_failed')}: {str(e)}")
        
        # 文档管理
        st.markdown("---")
        st.markdown(f"### {i18n('sidebar.document_management')}")
        
        uploaded_files = st.file_uploader(
            i18n('sidebar.upload_documents'),
            type=['pdf', 'txt', 'md', 'docx'],
            accept_multiple_files=True
        )
        
        if uploaded_files and st.button(i18n('sidebar.process_documents'), use_container_width=True):
            process_documents(uploaded_files)
        
        # 知识库信息
        st.markdown("---")
        st.markdown(f"### {i18n('sidebar.knowledge_base_info')}")
        
        info = st.session_state.vector_store_manager.get_collection_info()
        st.metric(i18n('sidebar.document_chunks'), info['document_count'])
        
        if st.button(i18n('sidebar.clear_knowledge_base'), use_container_width=True):
            try:
                st.session_state.vector_store_manager.delete_collection()
                st.session_state.vector_store_manager = VectorStoreManager(
                    persist_directory=st.session_state.config['vector_store']['persist_directory'],
                    collection_name=st.session_state.config['vector_store']['collection_name'],
                    embedding_model=st.session_state.config['embeddings']['model_name']
                )
                st.success(i18n('messages.knowledge_base_cleared'))
                st.rerun()
            except Exception as e:
                st.error(f"{i18n('messages.clear_failed')}: {str(e)}")


def process_documents(uploaded_files):
    """处理上传的文档"""
    i18n = st.session_state.i18n
    
    try:
        with st.spinner(i18n('messages.processing_documents')):
            temp_dir = Path("./temp_uploads")
            temp_dir.mkdir(exist_ok=True)
            
            all_documents = []
            
            for uploaded_file in uploaded_files:
                file_path = temp_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                documents = st.session_state.document_processor.process_document(str(file_path))
                all_documents.extend(documents)
                
                file_path.unlink()
            
            st.session_state.vector_store_manager.add_documents(all_documents)
            
            info = st.session_state.document_processor.get_document_info(all_documents)
            
            st.markdown(f"""
            <div class="success-box">
                <strong>{i18n('messages.document_processed')}</strong><br>
                • {i18n('messages.documents_count')}: {len(uploaded_files)}<br>
                • {i18n('messages.chunks_count')}: {info['total_chunks']}<br>
                • {i18n('messages.total_characters')}: {info['total_characters']:,}<br>
                • {i18n('messages.avg_chunk_size')}: {info['avg_chunk_size']} {i18n('messages.characters')}
            </div>
            """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"{i18n('messages.processing_failed')}: {str(e)}")


def render_chat_interface():
    """渲染聊天界面"""
    i18n = st.session_state.i18n
    
    st.markdown(f'<div class="main-header">{i18n("app.title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">{i18n("app.description")}</div>', unsafe_allow_html=True)
    
    if st.session_state.rag_chain is None:
        st.markdown(f"""
        <div class="info-box">
            <strong>{i18n('main.usage_instructions')}</strong><br>
            {i18n('main.step1')}<br>
            {i18n('main.step2')}<br>
            {i18n('main.step3')}
        </div>
        """, unsafe_allow_html=True)
        return
    
    info = st.session_state.vector_store_manager.get_collection_info()
    if info['document_count'] == 0:
        st.warning(i18n('main.empty_knowledge_base'))
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
                    with st.expander(i18n('main.view_sources')):
                        for i, source in enumerate(msg['sources'], 1):
                            st.markdown(f"""
                            <div class="source-card">
                                <strong>{i18n('main.source')} {i}:</strong> {source['source']} 
                                <span class="score-badge">{i18n('main.similarity')}: {source['score']:.2f}</span><br>
                                <em>{source['content']}</em>
                            </div>
                            """, unsafe_allow_html=True)
    
    # 输入区域
    user_question = st.chat_input(i18n('main.input_placeholder'))
    
    if user_question:
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_question
        })
        
        with st.chat_message("user"):
            st.write(user_question)
        
        with st.chat_message("assistant"):
            with st.spinner(i18n('main.thinking')):
                start_time = time.time()
                result = st.session_state.rag_chain.query(user_question)
                end_time = time.time()
                
                if result['error']:
                    st.error(f"{i18n('messages.answer_generation_failed')}: {result['error']}")
                else:
                    st.write(result['answer'])
                    
                    if result['sources']:
                        with st.expander(i18n('main.view_sources')):
                            for i, source in enumerate(result['sources'], 1):
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong>{i18n('main.source')} {i}:</strong> {source['source']} 
                                    <span class="score-badge">{i18n('main.similarity')}: {source['score']:.2f}</span><br>
                                    <em>{source['content']}</em>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    st.caption(f"{i18n('main.response_time')}: {end_time - start_time:.2f} {i18n('main.seconds')}")
                    
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