"""
国际化（i18n）模块
支持多语言界面
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class I18n:
    """国际化管理器"""
    
    def __init__(self, default_language: str = "zh_TW"):
        """
        初始化国际化管理器
        
        Args:
            default_language: 默认语言
        """
        self.default_language = default_language
        self.current_language = default_language
        self.translations: Dict[str, Dict[str, Any]] = {}
        
        # 加载所有语言文件
        self._load_languages()
    
    def _load_languages(self):
        """加载所有语言文件"""
        locales_dir = Path(__file__).parent.parent / "locales"
        
        if not locales_dir.exists():
            print(f"警告: 语言文件目录不存在: {locales_dir}")
            return
        
        for lang_file in locales_dir.glob("*.yaml"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = yaml.safe_load(f)
                print(f"已加载语言: {lang_code}")
            except Exception as e:
                print(f"加载语言文件失败 {lang_file}: {str(e)}")
    
    def set_language(self, language: str):
        """
        设置当前语言
        
        Args:
            language: 语言代码（如 'en', 'zh_TW'）
        """
        if language in self.translations:
            self.current_language = language
        else:
            print(f"警告: 语言 '{language}' 不存在，使用默认语言")
            self.current_language = self.default_language
    
    def get(self, key: str, default: str = "") -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键，使用点号分隔（如 'app.title'）
            default: 默认值
            
        Returns:
            翻译后的文本
        """
        try:
            keys = key.split('.')
            value = self.translations[self.current_language]
            
            for k in keys:
                value = value[k]
            
            return str(value)
        
        except (KeyError, TypeError):
            # 如果当前语言没有，尝试使用默认语言
            if self.current_language != self.default_language:
                try:
                    keys = key.split('.')
                    value = self.translations[self.default_language]
                    
                    for k in keys:
                        value = value[k]
                    
                    return str(value)
                except (KeyError, TypeError):
                    pass
            
            return default or key
    
    def get_available_languages(self) -> Dict[str, str]:
        """
        获取可用语言列表
        
        Returns:
            语言代码到语言名称的映射
        """
        return {
            "en": "English",
            "zh_TW": "繁體中文"
        }
    
    def __call__(self, key: str, default: str = "") -> str:
        """
        简化调用方式
        
        Args:
            key: 翻译键
            default: 默认值
            
        Returns:
            翻译后的文本
        """
        return self.get(key, default)