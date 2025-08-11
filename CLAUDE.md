# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

这是一个智能网站地图关键词分析工具，用于解析网站sitemap并提取关键词，然后通过API提交到后端系统。该项目主要使用Python 3.8+开发，采用异步编程模式处理大量URL。

### 核心功能
- 多格式sitemap解析（XML、RSS、压缩文件、TXT）
- 基于规则引擎的关键词提取
- URL过滤和去重
- 批量API提交（支持gzip压缩）
- 加密存储（66字符吉利密钥系统）
- 完善的日志和错误处理

## Development Commands

### 环境设置
```bash
# 安装依赖
pip install -r requirements.txt

# 复制并配置环境变量
cp .env.example .env
# 编辑.env填入实际配置（必需: SITEMAP_API_URL, SITEMAP_SECRET_KEY, ENCRYPTION_KEY, SITEMAP_URLS）

# 创建环境变量模板
python main.py --create-env
```

### 运行和测试
```bash
# 健康检查（验证配置和连接）
python main.py --health-check

# 处理默认sitemap列表（从SITEMAP_URLS环境变量读取）
python main.py

# 使用自定义sitemap文件
python main.py --sitemaps config/sitemaps.txt

# 调试模式运行
python main.py --log-level DEBUG

# 试运行模式（不实际提交数据）
python main.py --dry-run

# 查看帮助
python main.py --help
```

### 测试（当前无测试文件，需要创建）
```bash
# 运行测试（需要先创建测试）
pytest

# 运行异步测试
pytest -v --asyncio-mode=auto
```

## Architecture & Code Structure

### 项目架构分层

1. **入口层** (`main.py`)
   - 命令行参数解析
   - 环境变量加载
   - 健康检查执行
   - 主流程协调

2. **业务逻辑层** (`src/sitemap_analyzer.py`)
   - `SitemapKeywordAnalyzer`: 核心分析器类
   - 组件初始化和协调
   - sitemap解析流程管理
   - URL过滤和关键词提取编排

3. **数据处理流程**
   ```
   Sitemap URLs → Parser → URL列表 → 过滤器 → 关键词提取 → API提交
                              ↓           ↓           ↓
                         特殊处理器    规则引擎    批量压缩
   ```

4. **组件架构**

   - **解析器** (`src/parsers/`)
     - `SitemapParser`: 异步sitemap解析，支持递归和多格式
     - `SpecialSitemapHandler`: 特殊网站处理（itch.io等）
   
   - **提取器** (`src/extractors/`)
     - `RuleEngine`: URL规则匹配引擎，支持分层规则策略
     - `KeywordExtractor`: 关键词提取和清理
     - `KeywordProcessor`: 批量关键词处理
   
   - **API客户端** (`src/api/`)
     - `SimplifiedBackendClient`: 新架构的简化后端客户端（主要使用）
     - `BackendAPIClient`: 旧后端API（保留兼容）
     - SEO API相关模块已废弃但代码保留
   
   - **存储管理** (`src/storage/`)
     - `StorageManager`: 加密存储管理
     - `CacheManager`: 缓存管理
   
   - **工具类** (`src/utils/`)
     - `crypto`: 66字符吉利加密系统
     - `logger`: 日志配置和管理
     - `log_security`: 日志脱敏

### 关键设计模式

1. **异步并发处理**
   - 使用`aiohttp`进行异步HTTP请求
   - 信号量控制并发数量（默认10）
   - 批量处理和进度跟踪

2. **规则引擎系统**
   - 分层规则匹配（精确→去www→子域名→默认）
   - 预编译正则表达式提升性能
   - 动态规则添加和验证

3. **数据安全**
   - 66字符吉利加密密钥（兼容44字符Fernet）
   - 环境变量存储敏感信息
   - 日志自动脱敏（URL显示为`https://***`）

4. **容错机制**
   - 自动重试失败请求
   - 增量保存防止数据丢失
   - 详细的错误日志和堆栈跟踪

## Configuration Files

### 环境变量配置 (`.env`)
```bash
# 必需配置
SITEMAP_API_URL=http://localhost:5001/api/sitemap/keywords  # 后端API地址
SITEMAP_SECRET_KEY=your-secret-key-2024                     # API认证密钥
SITEMAP_URLS=https://site1.com/sitemap.xml,https://site2.com/sitemap.xml  # sitemap列表
ENCRYPTION_KEY=your-66-character-lucky-encryption-key       # 66字符加密密钥

# 已废弃（不再需要）
# SEO_API_URLS - SEO查询功能已移除
# BACKEND_API_URL - 已替换为SITEMAP_API_URL
# BACKEND_API_TOKEN - 已替换为SITEMAP_SECRET_KEY
```

### 配置文件结构
- `config/config.yaml` - 系统主配置（API设置、并发限制等）
- `config/game_url_rules.yaml` - URL提取规则配置
- `config/logging.conf` - 日志配置
- `config/url_rules.yaml` - URL规则备用配置

## Important Notes

### 当前架构要点

1. **简化的数据流程**
   - 直接从sitemap提取URL和关键词
   - 跳过SEO查询步骤（相关代码已注释但保留）
   - 直接提交URL-关键词映射到后端

2. **API集成**
   - 主要使用`SimplifiedBackendClient`
   - 支持gzip压缩减少传输数据量
   - 批量提交（默认100条/批）
   - 并发批次提交提高效率

3. **URL过滤策略**
   - 先应用排除规则过滤
   - 过滤已处理的URL避免重复
   - 支持特殊网站的自定义处理

4. **关键词提取策略**
   - 基于URL路径提取（最后路径段）
   - 清理特殊字符，分割连字符/下划线
   - 过滤停用词
   - 多关键词合并（逗号分隔）

### 注意事项

1. **配置验证**
   - 运行前必须配置环境变量
   - 使用`--health-check`验证配置
   - 加密密钥必须是66字符

2. **性能考虑**
   - 大量URL时注意内存使用
   - 调整并发数量避免过载
   - 批量大小影响API响应时间

3. **错误处理**
   - 检查日志文件了解详细错误
   - 网络错误会自动重试
   - 部分失败不影响整体流程

4. **数据安全**
   - 不要提交.env文件到版本控制
   - 定期轮换API密钥
   - 日志已自动脱敏

### 待改进项

1. 缺少单元测试和集成测试
2. SEO API相关代码可以完全移除
3. 可以添加更多的URL规则模板
4. 监控和指标收集可以增强
5. 文档可以更详细（API接口文档等）