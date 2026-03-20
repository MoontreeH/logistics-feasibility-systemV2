"""
Streamlit Cloud 主入口文件

物流业务智能可行性评估系统 - 真正LLM-native智能对话版本

特性：
- LLM-native架构，真正以LLM为核心
- 支持文件上传（Excel/CSV）
- 自然语言交互，无需固定流程
- 真正的语义理解和任务编排
"""

import streamlit as st
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入智能对话界面
from app.intelligent_chat_app import main

if __name__ == "__main__":
    main()
