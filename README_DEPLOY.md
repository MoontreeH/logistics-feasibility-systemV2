# 物流业务智能可行性评估系统

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

一个基于AI的物流成本评估和订单可行性分析系统。

## 功能特点

- 🤖 **AI智能评估**：自然语言输入，自动识别业务类型和参数
- 💰 **成本环节识别**：智能识别9大物流成本环节
- 📊 **选择性计算**：根据实际业务场景选择性计算成本
- 💹 **订单利润评估**：综合评估订单可行性（采购成本+物流成本）
- 💬 **智能问答**：基于RAG技术的物流知识问答
- 📈 **数据分析**：可视化成本结构和趋势分析

## 技术栈

- **前端**：Streamlit
- **AI模型**：DeepSeek-V3 (通过SiliconFlow API)
- **成本计算**：自定义9环节成本模型
- **向量数据库**：ChromaDB
- **数据可视化**：Plotly

## 部署方式

### 方式一：Streamlit Cloud（推荐）

1. Fork 这个仓库到你的 GitHub 账号
2. 访问 [Streamlit Cloud](https://streamlit.io/cloud)
3. 用 GitHub 账号登录
4. 点击 "New app"
5. 选择你的仓库和 `streamlit_app.py` 文件
6. 点击部署

### 方式二：本地运行

```bash
# 克隆仓库
git clone https://github.com/yourusername/logistics-feasibility-system.git
cd logistics-feasibility-system

# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run streamlit_app.py
```

### 方式三：Docker部署

```bash
# 构建镜像
docker build -t logistics-app .

# 运行容器
docker run -p 8501:8501 logistics-app
```

## 环境变量

创建 `.env` 文件并配置以下变量：

```env
SILICONFLOW_API_KEY=your_api_key_here
```

## 使用说明

1. 打开应用后，在侧边栏输入你的 SiliconFlow API Key
2. 在主界面输入业务描述，例如："每天100单办公用品，送到20公里外的写字楼"
3. 系统会自动识别业务类型和提取参数
4. 确认参数后，系统计算物流成本
5. 可以继续询问订单可行性（提供采购价和售价）

## 项目结构

```
logistics-feasibility-system/
├── app/                    # Web应用
│   ├── web_app.py         # 主Web应用
│   └── web_app_v2.py      # V2版本（支持智能参数收集）
├── src/                   # 源代码
│   ├── llm/              # LLM模块
│   ├── cost_engine/      # 成本计算引擎
│   ├── models/           # 数据模型
│   ├── rag/              # RAG模块
│   └── knowledge/        # 知识库
├── config/               # 配置文件
├── data/                 # 数据文件
├── streamlit_app.py      # Streamlit入口
├── requirements.txt      # Python依赖
└── README.md            # 项目说明
```

## 成本模型

系统基于9大物流成本环节：

1. 订单处理
2. 库存持有
3. 拣选作业
4. 包装
5. 加工（仅餐配）
6. 集货装车
7. 运输配送
8. 末端交付
9. 管理及间接费用

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue 或 Pull Request。
