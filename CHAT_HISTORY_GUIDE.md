# 聊天历史功能使用指南

本文档介绍 RAG 知识库问答系统的聊天历史功能。

## 🎯 功能概述

完整的聊天历史管理系统，包括：

✅ **会话管理**
- 创建新对话
- 切换历史对话
- 删除对话
- 自动保存所有对话

✅ **持久化存储**
- 使用 SQLite 数据库
- 刷新页面不丢失数据
- 支持导出对话

✅ **智能功能**
- 自动生成会话标题
- 显示消息数量
- 统计信息查看
- 搜索历史消息

## 📁 文件说明

### 核心文件

1. **`src/chat_history_manager.py`** - 聊天历史管理器
   - SQLite 数据库操作
   - 会话和消息的 CRUD
   - 搜索和统计功能

2. **`app_with_history.py`** - 完整版应用
   - 集成聊天历史功能
   - 多语言支持
   - 完整的用户界面

3. **`chat_history.db`** - SQLite 数据库（自动创建）
   - 存储所有会话和消息
   - 自动备份建议

## 🚀 快速开始

### 启动应用

```bash
# 使用完整版（推荐）
streamlit run app_with_history.py --server.port 8501 --server.address 0.0.0.0

# 或使用基础版（无聊天历史）
streamlit run app_i18n.py --server.port 8501 --server.address 0.0.0.0
```

## 📖 使用说明

### 1. 创建新对话

1. 点击侧边栏的 **"➕ 新对话"** 按钮
2. 系统自动创建新会话
3. 会话标题默认为 "新对话 - 时间"
4. 第一次提问后，标题会自动更新为问题内容

### 2. 切换历史对话

1. 在侧边栏查看所有历史会话
2. 点击会话标题切换到该对话
3. 当前会话显示 📌 图标
4. 会话按更新时间倒序排列

### 3. 删除对话

1. 点击会话右侧的 **🗑️** 按钮
2. 确认删除
3. 如果删除的是当前会话，会自动创建新会话

### 4. 查看统计信息

1. 点击侧边栏的 **📊** 按钮
2. 显示统计卡片：
   - 总会话数
   - 总消息数
   - 用户消息数
   - 助手消息数

### 5. 导出对话

```python
# 在 Python 中导出
from src.chat_history_manager import ChatHistoryManager

manager = ChatHistoryManager()
manager.export_session(
    session_id="your_session_id",
    output_path="exported_chat.json"
)
```

## 🗄️ 数据库结构

### 表结构

#### sessions 表（会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | TEXT | 会话 ID（主键） |
| title | TEXT | 会话标题 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| message_count | INTEGER | 消息数量 |

#### messages 表（消息）

| 字段 | 类型 | 说明 |
|------|------|------|
| message_id | INTEGER | 消息 ID（主键） |
| session_id | TEXT | 所属会话 ID |
| role | TEXT | 角色（user/assistant） |
| content | TEXT | 消息内容 |
| sources | TEXT | 来源信息（JSON） |
| created_at | TIMESTAMP | 创建时间 |

## 💡 高级功能

### 1. 搜索历史消息

```python
from src.chat_history_manager import ChatHistoryManager

manager = ChatHistoryManager()

# 搜索包含关键词的消息
results = manager.search_messages("关键词", limit=20)

for result in results:
    print(f"会话: {result['session_title']}")
    print(f"内容: {result['content']}")
    print(f"时间: {result['created_at']}")
```

### 2. 获取统计信息

```python
stats = manager.get_statistics()

print(f"总会话数: {stats['total_sessions']}")
print(f"总消息数: {stats['total_messages']}")
print(f"用户消息: {stats['user_messages']}")
print(f"助手消息: {stats['assistant_messages']}")
```

### 3. 批量导出

```python
# 导出所有会话
sessions = manager.get_all_sessions()

for session in sessions:
    output_path = f"exports/session_{session['session_id']}.json"
    manager.export_session(session['session_id'], output_path)
```

## 🔧 配置选项

### 数据库位置

默认：`./chat_history.db`

自定义：

```python
from src.chat_history_manager import ChatHistoryManager

# 使用自定义路径
manager = ChatHistoryManager(db_path="/path/to/your/database.db")
```

### 会话列表限制

默认显示最近 50 个会话

修改：

```python
# 在 app_with_history.py 中
sessions = st.session_state.chat_history_manager.get_all_sessions(limit=100)
```

## 📊 性能优化

### 1. 数据库索引

已创建的索引：
- `idx_messages_session` - 消息按会话查询
- `idx_sessions_updated` - 会话按更新时间排序

### 2. 定期清理

```python
# 删除旧会话（保留最近 100 个）
sessions = manager.get_all_sessions(limit=1000)
old_sessions = sessions[100:]

for session in old_sessions:
    manager.delete_session(session['session_id'])
```

### 3. 数据库备份

```bash
# 定期备份数据库
cp chat_history.db backups/chat_history_$(date +%Y%m%d).db

# 或使用 SQLite 备份命令
sqlite3 chat_history.db ".backup backups/chat_history_$(date +%Y%m%d).db"
```

## 🐛 故障排查

### 1. 数据库锁定

**问题**：`database is locked` 错误

**解决**：
```python
# 增加超时时间
conn = sqlite3.connect(self.db_path, timeout=30)
```

### 2. 消息丢失

**问题**：刷新后消息消失

**检查**：
1. 确认使用 `app_with_history.py`
2. 检查数据库文件是否存在
3. 查看数据库权限

### 3. 会话列表不更新

**解决**：
```python
# 强制刷新会话列表
st.rerun()
```

## 🔐 安全建议

1. **定期备份数据库**
   ```bash
   # 每天备份
   0 2 * * * cp /path/to/chat_history.db /backups/chat_history_$(date +\%Y\%m\%d).db
   ```

2. **限制数据库访问权限**
   ```bash
   chmod 600 chat_history.db
   ```

3. **敏感信息处理**
   - 不要在对话中包含密码或密钥
   - 定期清理敏感会话
   - 考虑加密存储

## 📚 API 参考

### ChatHistoryManager 类

#### 初始化
```python
manager = ChatHistoryManager(db_path="./chat_history.db")
```

#### 会话管理
```python
# 创建会话
manager.create_session(session_id, title)

# 获取所有会话
sessions = manager.get_all_sessions(limit=50)

# 更新会话标题
manager.update_session_title(session_id, new_title)

# 删除会话
manager.delete_session(session_id)
```

#### 消息管理
```python
# 添加消息
manager.add_message(session_id, role, content, sources)

# 获取会话消息
messages = manager.get_session_messages(session_id)

# 搜索消息
results = manager.search_messages(query, limit=20)
```

#### 工具函数
```python
# 获取统计信息
stats = manager.get_statistics()

# 导出会话
manager.export_session(session_id, output_path)
```

## 🎨 自定义界面

### 修改会话显示

在 `app_with_history.py` 中：

```python
# 自定义会话标题显示
for session in sessions:
    # 添加时间戳
    time_str = session['updated_at'].split()[0]
    title = f"{session['title']} ({time_str})"
    
    # 添加消息数量
    title = f"{session['title']} [{session['message_count']}]"
```

### 添加会话分类

```python
# 按日期分组
from datetime import datetime

sessions_by_date = {}
for session in sessions:
    date = session['created_at'].split()[0]
    if date not in sessions_by_date:
        sessions_by_date[date] = []
    sessions_by_date[date].append(session)

# 显示分组
for date, date_sessions in sessions_by_date.items():
    st.markdown(f"### {date}")
    for session in date_sessions:
        # 显示会话
        pass
```

## 🚀 未来功能

计划添加的功能：

- [ ] 会话标签和分类
- [ ] 会话搜索功能
- [ ] 批量导出和导入
- [ ] 会话分享功能
- [ ] 对话摘要生成
- [ ] 多用户支持

## ❓ 常见问题

**Q: 如何迁移现有对话？**

A: 使用导出功能：
```python
# 导出所有会话
sessions = manager.get_all_sessions()
for session in sessions:
    manager.export_session(session['session_id'], f"backup/{session['session_id']}.json")
```

**Q: 数据库文件太大怎么办？**

A: 定期清理旧会话或使用 SQLite 的 VACUUM 命令：
```bash
sqlite3 chat_history.db "VACUUM;"
```

**Q: 如何恢复删除的会话？**

A: 从备份中恢复：
```bash
cp backups/chat_history_backup.db chat_history.db
```

---

如有问题，请查看项目文档或提交 Issue。