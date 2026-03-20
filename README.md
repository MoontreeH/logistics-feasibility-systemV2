# 物流业务智能可行性评估系统

一个基于AI和成本模型的物流业务评估工具，支持TOB企业购和餐配业务的成本估算与可行性分析。

## 🎯 系统特性

- **🤖 AI驱动**: 自然语言理解，自动识别业务类型和提取参数
- **📊 精确计算**: 9大成本环节全覆盖，计算精确到元
- **💡 智能建议**: 数据驱动的优化建议，量化节省金额
- **🔍 知识检索**: 基于RAG技术，支持语义检索和问答
- **🌐 Web界面**: 可视化操作，支持图表展示
- **📁 批量处理**: Excel导入导出，支持批量评估

## 📋 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户交互层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Web界面     │  │  CLI工具     │  │  Excel导入       │  │
│  │  (Streamlit) │  │  (命令行)    │  │  (批量处理)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    智能理解层 (LLM)                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ 意图识别     │  │ 实体抽取     │  │ 多轮对话     │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    成本计算引擎                        │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │ │
│  │  │订单处理 │ │仓储持有 │ │拣选加工 │ │运输配送 │    │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │ │
│  │  │末端交付 │ │逆向处理 │ │管理分摊 │ │...      │    │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              知识层 (RAG + 知识库)                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ 向量数据库   │  │ 文档检索     │  │ 行业知识     │ │ │
│  │  │ (ChromaDB)   │  │ (语义搜索)   │  │ (最佳实践)   │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式1：本地运行

```bash
# 1. 克隆项目
git clone <repository-url>
cd logistics-feasibility-system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置API密钥
# 编辑 .env 文件，设置 SILICONFLOW_API_KEY

# 4. 启动Web界面
streamlit run app/web_app.py

# 或启动CLI
python enhanced_cli.py
```

### 方式2：Docker部署

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 访问应用
# 打开浏览器访问 http://localhost:8501
```

## 📖 使用指南

### Web界面

1. **成本评估**
   - 在文本框中输入业务描述
   - 点击"开始评估"按钮
   - 查看成本分析、优化建议

2. **智能问答**
   - 在对话框中输入问题
   - 支持追问和假设分析

3. **数据分析**
   - 调整参数进行What-If分析
   - 查看成本趋势图表

4. **知识库管理**
   - 上传文档扩充知识库
   - 测试知识检索效果

### CLI工具

```bash
# 启动增强版CLI
python enhanced_cli.py

# 示例交互
> 我们想接一个企业客户，每天100单办公用品，送到20公里外的写字楼

系统: [输出完整评估报告]

> 运输成本为什么这么高？

系统: [输出运输成本详细构成]

> 如果日订单增加到150单会怎样？

系统: [输出假设分析结果]
```

### Excel批量处理

```python
from src.utils.excel_handler import ExcelHandler

# 创建导入模板
ExcelHandler.create_import_template("template.xlsx")

# 导入数据
scenarios = ExcelHandler.import_from_excel("data.xlsx")

# 批量评估并导出
results = [assessor.assess_from_text(str(s)) for s in scenarios]
ExcelHandler.export_report_to_excel(results, "report.xlsx")
```

## 📊 成本模型

### 9大成本环节

| 环节 | 计费方式 | 适用业务 |
|------|----------|----------|
| 订单处理 | 2.5元/行 | 通用 |
| 库存持有 | 资金成本+租金+风险 | 通用 |
| 拣选作业 | 0.5-0.7元/件 | 通用 |
| 加工包装 | 2-5元/包 | 通用 |
| 集货装车 | 25元/工时 | 通用 |
| 运输配送 | 3.5-4.8元/公里 | 通用 |
| 末端交付 | 卸货+上楼费 | TOB |
| 逆向处理 | 退货处理+报废 | 通用 |
| 管理分摊 | 直接成本×15% | 通用 |

### 费率配置

费率配置位于 `config/rates.yaml`，可根据实际业务调整：

```yaml
transportation:
  normal_vehicle_variable:
    rate: 3.5  # 常温车变动成本
  cold_vehicle_variable:
    rate: 4.8  # 冷藏车变动成本
delivery:
  upstairs:
    rate: 10.0  # 上楼费（元/层）
```

## 🧠 智能功能

### 1. 意图识别
自动识别TOB企业购或餐配业务，支持关键词降级策略。

### 2. 实体抽取
从自然语言提取关键参数：订单数、重量、距离、楼层等。

### 3. 数据驱动建议
每条建议包含：
- 📊 数据支撑（具体数字）
- 💰 预期节省金额和比例
- 📝 具体行动步骤
- ⭐ 实施难度和优先级

### 4. RAG知识检索
- 基于ChromaDB向量数据库
- 语义检索，支持自然语言查询
- 自动加载系统知识库

### 5. 假设分析
支持What-If分析，探索不同业务场景的成本变化。

## 🛠️ 开发指南

### 项目结构

```
logistics-feasibility-system/
├── app/                      # Web应用
│   └── web_app.py           # Streamlit主应用
├── config/                   # 配置文件
│   ├── rates.yaml           # 成本费率
│   └── prompts.yaml         # LLM Prompt模板
├── src/                      # 源代码
│   ├── models/              # 数据模型
│   ├── cost_engine/         # 成本计算引擎
│   ├── llm/                 # LLM模块
│   ├── knowledge/           # 知识库模块
│   ├── rag/                 # RAG模块
│   └── utils/               # 工具函数
├── data/                     # 数据目录
│   ├── chroma_db/          # 向量数据库
│   └── knowledge_base/     # 知识库数据
├── tests/                    # 测试
├── Dockerfile               # Docker镜像
├── docker-compose.yml       # Docker Compose配置
└── requirements.txt         # 依赖列表
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_cost_engine.py -v

# 测试RAG功能
python -c "from src.rag import RAGEngine; rag = RAGEngine(); print(rag.query('TOB企业购特点'))"
```

## 📝 API文档

### EnhancedAssessor

```python
from src.llm import EnhancedAssessor

assessor = EnhancedAssessor()

# 评估业务场景
result = assessor.assess_from_text("每天100单办公用品...")

# 处理追问
response = assessor.handle_follow_up("运输成本为什么这么高？")

# 假设分析
analysis = assessor.what_if_analysis({"monthly_order_count": 4500})
```

### RAGEngine

```python
from src.rag import RAGEngine

rag = RAGEngine()

# 查询知识库
result = rag.query("如何降低配送成本？")

# 添加文档
rag.add_file_to_knowledge_base("document.txt")
```

## 🔧 配置说明

### 环境变量

创建 `.env` 文件：

```env
SILICONFLOW_API_KEY=your_api_key_here
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V3
```

### 自定义知识库

1. 将文档放入 `data/knowledge_base/`
2. 支持格式：TXT、Markdown、Excel
3. 在Web界面"知识库管理"页面上传

## 📈 版本历史

- **v1.0.0** (当前)
  - ✅ 完整的Web界面
  - ✅ RAG知识检索
  - ✅ Excel批量处理
  - ✅ Docker部署支持

- **v0.3.0**
  - ✅ 环节级成本查询
  - ✅ 数据驱动建议
  - ✅ 智能追问处理
  - ✅ 知识库系统

- **v0.2.0**
  - ✅ LLM智能理解
  - ✅ 意图识别
  - ✅ 实体抽取
  - ✅ 多轮对话

- **v0.1.0**
  - ✅ 基础成本计算
  - ✅ 9大环节模型
  - ✅ CLI界面

## 🤝 贡献指南

欢迎提交Issue和PR！

## 📄 许可证

MIT License

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至：[your-email@example.com]

---

**注意**: 本系统仅供学习和参考使用，实际业务决策请结合专业判断。
