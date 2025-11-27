"""
聊天历史管理模块
使用 SQLite 数据库持久化聊天记录
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class ChatHistoryManager:
    """聊天历史管理器"""
    
    def __init__(self, db_path: str = "./chat_history.db"):
        """
        初始化聊天历史管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
        """)
        
        # 创建消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON messages(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_updated 
            ON sessions(updated_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, title: str = "新对话") -> bool:
        """
        创建新会话
        
        Args:
            session_id: 会话 ID
            title: 会话标题
            
        Returns:
            是否创建成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sessions (session_id, title)
                VALUES (?, ?)
            """, (session_id, title))
            
            conn.commit()
            conn.close()
            return True
        
        except sqlite3.IntegrityError:
            # 会话已存在
            return False
        except Exception as e:
            print(f"创建会话失败: {str(e)}")
            return False
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None
    ) -> bool:
        """
        添加消息到会话
        
        Args:
            session_id: 会话 ID
            role: 角色（user 或 assistant）
            content: 消息内容
            sources: 来源信息（仅 assistant 消息）
            
        Returns:
            是否添加成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 添加消息
            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
            
            cursor.execute("""
                INSERT INTO messages (session_id, role, content, sources)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, content, sources_json))
            
            # 更新会话的更新时间和消息数量
            cursor.execute("""
                UPDATE sessions
                SET updated_at = CURRENT_TIMESTAMP,
                    message_count = message_count + 1
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            print(f"添加消息失败: {str(e)}")
            return False
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """
        获取会话的所有消息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role, content, sources, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            
            messages = []
            for row in cursor.fetchall():
                role, content, sources_json, created_at = row
                
                message = {
                    'role': role,
                    'content': content if role == 'user' else None,
                    'answer': content if role == 'assistant' else None,
                    'created_at': created_at
                }
                
                if sources_json:
                    message['sources'] = json.loads(sources_json)
                
                messages.append(message)
            
            conn.close()
            return messages
        
        except Exception as e:
            print(f"获取消息失败: {str(e)}")
            return []
    
    def get_all_sessions(self, limit: int = 50) -> List[Dict]:
        """
        获取所有会话列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            会话列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, title, created_at, updated_at, message_count
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                session_id, title, created_at, updated_at, message_count = row
                sessions.append({
                    'session_id': session_id,
                    'title': title,
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'message_count': message_count
                })
            
            conn.close()
            return sessions
        
        except Exception as e:
            print(f"获取会话列表失败: {str(e)}")
            return []
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """
        更新会话标题
        
        Args:
            session_id: 会话 ID
            title: 新标题
            
        Returns:
            是否更新成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sessions
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (title, session_id))
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            print(f"更新会话标题失败: {str(e)}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话及其所有消息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否删除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除会话（消息会因为外键级联删除）
            cursor.execute("""
                DELETE FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            print(f"删除会话失败: {str(e)}")
            return False
    
    def search_messages(self, query: str, limit: int = 20) -> List[Dict]:
        """
        搜索消息
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的消息列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT m.session_id, s.title, m.role, m.content, m.created_at
                FROM messages m
                JOIN sessions s ON m.session_id = s.session_id
                WHERE m.content LIKE ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (f'%{query}%', limit))
            
            results = []
            for row in cursor.fetchall():
                session_id, title, role, content, created_at = row
                results.append({
                    'session_id': session_id,
                    'session_title': title,
                    'role': role,
                    'content': content,
                    'created_at': created_at
                })
            
            conn.close()
            return results
        
        except Exception as e:
            print(f"搜索消息失败: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总会话数
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]
            
            # 总消息数
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # 用户消息数
            cursor.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'")
            user_messages = cursor.fetchone()[0]
            
            # 助手消息数
            cursor.execute("SELECT COUNT(*) FROM messages WHERE role = 'assistant'")
            assistant_messages = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'user_messages': user_messages,
                'assistant_messages': assistant_messages
            }
        
        except Exception as e:
            print(f"获取统计信息失败: {str(e)}")
            return {
                'total_sessions': 0,
                'total_messages': 0,
                'user_messages': 0,
                'assistant_messages': 0
            }
    
    def export_session(self, session_id: str, output_path: str) -> bool:
        """
        导出会话到 JSON 文件
        
        Args:
            session_id: 会话 ID
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取会话信息
            cursor.execute("""
                SELECT session_id, title, created_at, updated_at
                FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            session_row = cursor.fetchone()
            if not session_row:
                return False
            
            session_id, title, created_at, updated_at = session_row
            
            # 获取消息
            cursor.execute("""
                SELECT role, content, sources, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            
            messages = []
            for row in cursor.fetchall():
                role, content, sources_json, msg_created_at = row
                message = {
                    'role': role,
                    'content': content,
                    'created_at': msg_created_at
                }
                if sources_json:
                    message['sources'] = json.loads(sources_json)
                messages.append(message)
            
            conn.close()
            
            # 导出到文件
            export_data = {
                'session_id': session_id,
                'title': title,
                'created_at': created_at,
                'updated_at': updated_at,
                'messages': messages
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            print(f"导出会话失败: {str(e)}")
            return False