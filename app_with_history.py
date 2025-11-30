"""
RAG 知识库问答系统 - 完整版（多语言 + 聊天历史）
"""
import requests
import streamlit as st
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import uuid
from datetime import datetime

from src.document_processor import DocumentProcessor
from src.vector_store_manager import VectorStoreManager
from src.rag_chain import RAGChain
from src.i18n import I18n
from src.chat_history_manager import ChatHistoryManager

# 加载环境变量
load_dotenv()
FASTAPI_BASE = os.getenv("FASTAPI_BASE", "http://localhost:8000")
FASTAPI_URL = f"{FASTAPI_BASE}/query"

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
    .session-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 5px;
        cursor: pointer;
        transition: background 0.2s;
    }
    .session-item:hover {
        background: #f0f0f0;
    }
    .session-item.active {
        background: #e8f4f8;
        border-left: 3px solid #667eea;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def load_config():
    """加载配置文件"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_backend_collection_info():
    try:
        r = requests.get(f"{FASTAPI_BASE}/vector-store/info", timeout=10)
        return r.json()
    except Exception:
        return st.session_state.vector_store_manager.get_collection_info()


def initialize_session_state():
    """初始化会话状态"""
    if 'i18n' not in st.session_state:
        st.session_state.i18n = I18n(default_language="zh_TW")
    
    if 'config' not in st.session_state:
        st.session_state.config = load_config()
    
    if 'chat_history_manager' not in st.session_state:
        st.session_state.chat_history_manager = ChatHistoryManager()
    
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.chat_history_manager.create_session(
            st.session_state.current_session_id,
            f"新对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    
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
    
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []


def render_sidebar():
    """渲染侧边栏"""
    i18n = st.session_state.i18n
    
    with st.sidebar:
        # 语言选择
        st.markdown(f"### {i18n('sidebar.language_settings')}")
        available_languages = i18n.get_available_languages()
        
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
        
        # 聊天历史
        st.markdown("### 💬 聊天历史")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("➕ 新对话", use_container_width=True):
                new_session_id = str(uuid.uuid4())
                st.session_state.chat_history_manager.create_session(
                    new_session_id,
                    f"新对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                st.session_state.current_session_id = new_session_id
                st.session_state.chat_messages = []
                st.rerun()
        
        with col2:
            if st.button("📊", use_container_width=True):
                st.session_state.show_stats = not st.session_state.get('show_stats', False)
                st.rerun()
        
        # 显示统计信息
        if st.session_state.get('show_stats', False):
            stats = st.session_state.chat_history_manager.get_statistics()
            st.markdown(f"""
            <div class="stat-card">
                <h4>📊 统计信息</h4>
                <p>总会话: {stats['total_sessions']}</p>
                <p>总消息: {stats['total_messages']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 会话列表
        sessions = st.session_state.chat_history_manager.get_all_sessions()
        
        for session in sessions:
            is_current = session['session_id'] == st.session_state.current_session_id
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if st.button(
                    f"{'📌 ' if is_current else ''}{session['title'][:30]}",
                    key=f"session_{session['session_id']}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary"
                ):
                    st.session_state.current_session_id = session['session_id']
                    st.session_state.chat_messages = st.session_state.chat_history_manager.get_session_messages(
                        session['session_id']
                    )
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{session['session_id']}", use_container_width=True):
                    st.session_state.chat_history_manager.delete_session(session['session_id'])
                    if session['session_id'] == st.session_state.current_session_id:
                        new_session_id = str(uuid.uuid4())
                        st.session_state.chat_history_manager.create_session(
                            new_session_id,
                            f"新对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                        st.session_state.current_session_id = new_session_id
                        st.session_state.chat_messages = []
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
                        st.session_state.llm_provider = llm_provider
                        st.session_state.llm_model_name = model_name
                        st.session_state.llm_base_url = base_url
                        st.session_state.llm_api_key = api_key
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
        
        info = get_backend_collection_info()
        st.metric(i18n('sidebar.document_chunks'), info['document_count'])
        
        if st.button(i18n('sidebar.clear_knowledge_base'), use_container_width=True):
            try:
                resp = requests.delete(f"{FASTAPI_BASE}/vector-store/collection", timeout=30)
                if resp.status_code == 200 and resp.json().get('status') == 'cleared':
                    # 重新初始化本地管理器以保持状态一致
                    st.session_state.vector_store_manager = VectorStoreManager(
                        persist_directory=st.session_state.config['vector_store']['persist_directory'],
                        collection_name=st.session_state.config['vector_store']['collection_name'],
                        embedding_model=st.session_state.config['embeddings']['model_name']
                    )
                    st.success(i18n('messages.knowledge_base_cleared'))
                    st.rerun()
                else:
                    st.error(f"{i18n('messages.clear_failed')}: {resp.text}")
            except Exception as e:
                st.error(f"{i18n('messages.clear_failed')}: {str(e)}")


def process_documents(uploaded_files):
    i18n = st.session_state.i18n
    try:
        with st.spinner(i18n('messages.processing_documents')):
            files_payload = []
            for uf in uploaded_files:
                try:
                    content = uf.getvalue()
                except Exception:
                    content = uf.getbuffer()
                files_payload.append(('files', (uf.name, content, uf.type or 'application/octet-stream')))
            r = requests.post(f"{FASTAPI_BASE}/vector-store/upload_async", files=files_payload, timeout=20)
            r.raise_for_status()
            tid = r.json().get('task_id')
            if not tid:
                st.error(i18n('messages.processing_failed'))
                return
            progress = st.progress(0)
            start = time.time()
            inserted = 0
            total = len(uploaded_files)
            while True:
                s = requests.get(f"{FASTAPI_BASE}/tasks/{tid}", timeout=10)
                info = s.json()
                status = info.get('status')
                processed = info.get('processed_files', 0)
                inserted = info.get('inserted', inserted)
                progress.progress(min(int(processed * 100 / max(total,1)), 100))
                if status == 'done':
                    break
                if status == 'error':
                    st.error(f"{i18n('messages.processing_failed')}: {info.get('error')}")
                    return
                if time.time() - start > 300:
                    st.error(i18n('messages.processing_failed'))
                    return
                time.sleep(1)
            info_resp = {}
            try:
                rr = requests.get(f"{FASTAPI_BASE}/vector-store/info", timeout=10)
                info_resp = rr.json()
            except Exception:
                info_resp = st.session_state.vector_store_manager.get_collection_info()
            st.markdown(f"""
            <div class="success-box">
                <strong>{i18n('messages.document_processed')}</strong><br>
                • {i18n('messages.documents_count')}: {len(uploaded_files)}<br>
                • 新增切片: {inserted}<br>
                • 当前总切片: {info_resp.get('document_count', 0)}
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"{i18n('messages.processing_failed')}: {str(e)}")

def query_rag(question, session_id=None):
    payload = {"question": question, "session_id": session_id}
    lp = st.session_state.get('llm_provider')
    mn = st.session_state.get('llm_model_name')
    bu = st.session_state.get('llm_base_url')
    ak = st.session_state.get('llm_api_key')
    if lp or mn or bu or ak:
        payload.update({
            "llm_provider": lp,
            "model_name": mn,
            "base_url": bu,
            "api_key": ak
        })
    try:
        resp = requests.post(FASTAPI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            return {"answer": "", "sources": [], "error": data["error"]}
        return {"answer": data.get("answer", ""), "sources": data.get("sources", [])}
    except requests.RequestException as e:
        return {"answer": "", "sources": [], "error": f"后端不可用或请求失败: {e}"}
    except Exception as e:
        return {"answer": "", "sources": [], "error": str(e)}

def check_backend_alive():
    try:
        r = requests.get(f"{FASTAPI_BASE}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

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

    if not check_backend_alive():
        st.warning("后端服务未启动或不可用，请先启动 FastAPI（uvicorn backend.main:app --port 8000）")
    
    info = get_backend_collection_info()
    if info['document_count'] == 0:
        st.warning(i18n('main.empty_knowledge_base'))
    
    # 加载当前会话的消息
    if not st.session_state.chat_messages:
        st.session_state.chat_messages = st.session_state.chat_history_manager.get_session_messages(
            st.session_state.current_session_id
        )
    
    # 显示对话历史
    for msg in st.session_state.chat_messages:
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
    
    # 输入区域（页面底部，按 Enter 发送）
    user_question = st.chat_input(i18n('main.input_placeholder'))
    if user_question:
        st.session_state.chat_messages.append({'role': 'user', 'content': user_question})
        st.session_state.chat_history_manager.add_message(
            st.session_state.current_session_id,
            'user',
            user_question
        )
        with st.chat_message("user"):
            st.write(user_question)
        with st.chat_message("assistant"):
            with st.spinner(i18n('main.thinking')):
                start_time = time.time()
                result = query_rag(user_question, st.session_state.current_session_id)
                end_time = time.time()
                error_msg = result.get('error')
                answer = result.get('answer')
                sources = result.get('sources', [])
                if error_msg:
                    st.error(f"{i18n('messages.answer_generation_failed')}: {error_msg}")
                else:
                    if answer:
                        st.write(answer)
                    if sources:
                        with st.expander(i18n('main.view_sources')):
                            for i, source in enumerate(sources, 1):
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong>{i18n('main.source')} {i}:</strong> {source['source']} 
                                    <span class="score-badge">{i18n('main.similarity')}: {source['score']:.2f}</span><br>
                                    <em>{source['content']}</em>
                                </div>
                                """, unsafe_allow_html=True)
                    st.caption(f"{i18n('main.response_time')}: {end_time - start_time:.2f} {i18n('main.seconds')}")
                    st.session_state.chat_messages.append({'role': 'assistant', 'answer': answer, 'sources': sources})
                    st.session_state.chat_history_manager.add_message(
                        st.session_state.current_session_id,
                        'assistant',
                        answer,
                        sources
                    )
                    sessions = st.session_state.chat_history_manager.get_all_sessions(limit=1)
                    if sessions and sessions[0]['session_id'] == st.session_state.current_session_id:
                        if sessions[0]['message_count'] == 2:
                            title = user_question[:30] + "..." if len(user_question) > 30 else user_question
                            st.session_state.chat_history_manager.update_session_title(
                                st.session_state.current_session_id,
                                title
                            )


def main():
    """主函数"""
    initialize_session_state()
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()
