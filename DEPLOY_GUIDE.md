# Streamlit Cloud 部署指南

## 准备工作

### 1. 安装 Git

1. 访问 https://git-scm.com/download/win
2. 下载 Git for Windows
3. 运行安装程序，使用默认设置即可

### 2. 配置 Git

打开命令提示符或 PowerShell，运行：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

## 部署步骤

### 步骤 1：在 GitHub 上创建仓库

1. 访问 https://github.com
2. 登录你的 GitHub 账号
3. 点击右上角的 "+" 按钮，选择 "New repository"
4. 填写仓库信息：
   - Repository name: `logistics-feasibility-system`
   - Description: `物流业务智能可行性评估系统`
   - 选择 "Public"（公开）
   - 勾选 "Add a README file"
5. 点击 "Create repository"

### 步骤 2：上传代码到 GitHub

#### 方法 A：使用 Git 命令行（推荐）

1. 打开命令提示符，进入项目目录：
```bash
cd e:\tese-trae\logistics-feasibility-system
```

2. 初始化 Git 仓库：
```bash
git init
```

3. 添加所有文件：
```bash
git add .
```

4. 提交更改：
```bash
git commit -m "Initial commit"
```

5. 连接到你的 GitHub 仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）：
```bash
git remote add origin https://github.com/YOUR_USERNAME/logistics-feasibility-system.git
```

6. 推送到 GitHub：
```bash
git push -u origin main
```

#### 方法 B：使用 GitHub Desktop（图形界面）

1. 下载并安装 GitHub Desktop：https://desktop.github.com/
2. 登录你的 GitHub 账号
3. 选择 "File" → "Add local repository"
4. 选择 `e:\tese-trae\logistics-feasibility-system` 文件夹
5. 填写提交信息，点击 "Commit to main"
6. 点击 "Publish repository"

#### 方法 C：直接上传文件（最简单）

1. 访问 https://github.com/YOUR_USERNAME/logistics-feasibility-system
2. 点击 "Add file" → "Upload files"
3. 将 `e:\tese-trae\logistics-feasibility-system` 中的所有文件和文件夹拖拽到上传区域
4. 注意：需要保持文件夹结构
5. 点击 "Commit changes"

### 步骤 3：部署到 Streamlit Cloud

1. 访问 https://streamlit.io/cloud
2. 点击 "Sign in with GitHub"
3. 授权 Streamlit 访问你的 GitHub 账号
4. 点击 "New app"
5. 配置部署选项：
   - **Repository**: 选择 `YOUR_USERNAME/logistics-feasibility-system`
   - **Branch**: 选择 `main` 或 `master`
   - **Main file path**: 输入 `streamlit_app.py`
   - **App URL**: 可以自定义，例如 `logistics-assessment`

6. 点击 "Deploy!"

7. 等待部署完成（通常需要 2-5 分钟）

### 步骤 4：配置 API Key

由于 API Key 是敏感信息，不能上传到 GitHub，需要在 Streamlit Cloud 中配置：

1. 在 Streamlit Cloud 中打开你的应用
2. 点击右上角的 "⋮"（三个点）
3. 选择 "Settings"
4. 点击 "Secrets"
5. 添加以下配置：

```toml
SILICONFLOW_API_KEY = "你的API密钥"
```

6. 点击 "Save"
7. 应用会自动重新部署

### 步骤 5：验证部署

1. 等待应用重新部署完成
2. 点击应用链接访问
3. 在侧边栏输入 API Key
4. 测试功能是否正常

## 更新应用

当你修改代码后，需要更新部署：

### 使用 Git 命令行

```bash
cd e:\tese-trae\logistics-feasibility-system
git add .
git commit -m "更新说明"
git push origin main
```

Streamlit Cloud 会自动检测代码更新并重新部署。

### 使用 GitHub Desktop

1. 在 GitHub Desktop 中查看更改
2. 填写提交信息
3. 点击 "Commit to main"
4. 点击 "Push origin"

## 常见问题

### Q1: 部署失败，提示缺少依赖

**解决**：确保 `requirements.txt` 文件包含所有必要的依赖包。

### Q2: 应用启动但显示错误

**解决**：
1. 检查 Streamlit Cloud 的日志（在应用页面点击 "Manage app" → "Logs"）
2. 确认 `streamlit_app.py` 文件路径正确
3. 检查 API Key 是否正确配置

### Q3: 如何更改应用名称或URL

**解决**：
1. 在 Streamlit Cloud 中打开应用
2. 点击 "Settings"
3. 修改 "App URL"
4. 保存后会自动重新部署

### Q4: 如何设置自定义域名

**解决**：
1. 在 Streamlit Cloud 中打开应用
2. 点击 "Settings"
3. 找到 "Custom domain" 部分
4. 按照说明配置 DNS

## 文件说明

确保以下文件已上传到 GitHub：

- ✅ `streamlit_app.py` - Streamlit 入口文件
- ✅ `requirements.txt` - Python 依赖
- ✅ `.streamlit/config.toml` - Streamlit 配置
- ✅ `app/` - Web 应用代码
- ✅ `src/` - 源代码
- ✅ `config/` - 配置文件
- ✅ `data/` - 数据文件
- ❌ `.env` - 环境变量文件（不要上传，包含敏感信息）
- ❌ `__pycache__/` - Python 缓存（已添加到 .gitignore）

## 获取帮助

如果遇到问题：

1. 查看 Streamlit Cloud 文档：https://docs.streamlit.io/streamlit-community-cloud
2. 查看 GitHub 文档：https://docs.github.com
3. 在 GitHub 上提交 Issue

## 下一步

部署成功后，你可以：

1. 分享应用链接给同事使用
2. 在 GitHub 上继续开发新功能
3. 配置自定义域名
4. 设置访问权限（如果需要限制访问）

祝你部署顺利！🚀
