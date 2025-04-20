# UnifiScrapy

使用GraphQL API爬取Ubiquiti产品发布信息，存储到MongoDB数据库，并提供交互式时间轴可视化工具的Python项目。

## 项目简介

UnifiScrapy是一个完整的解决方案，用于获取、存储和可视化Ubiquiti产品的发布信息。项目包含两个主要部分：

### 1. 爬虫部分

爬虫模块通过GraphQL API获取最新的产品版本信息，并将其保存至MongoDB数据库：
- 使用GraphQL API获取数据，无需浏览器自动化
- 增量更新机制，避免重复处理
- 断点续传功能，支持中断后继续爬取
- 完整的错误处理和日志记录
- 可配置的参数和灵活的扩展性

### 2. 时间轴展示部分

时间轴可视化工具将MongoDB中的数据转换为交互式HTML时间轴：
- 所有Ubiquiti产品发布的可视化时间轴
- 按产品线分组显示
- 支持按版本类型(GA/RC等)过滤查看
- 按年份分组折叠显示
- 显示详细的发布信息，包括版本号、发布日期、发布说明等
- 支持下载链接直接获取固件

## 环境要求

- Python 3.8+
- MongoDB 4.0+
- 网络连接
- pymongo
- jinja2（时间轴生成）

## 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/UnifiScrapy.git
cd UnifiScrapy
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
```

编辑`.env`文件，设置MongoDB连接参数：
```
MONGO_URI=mongodb://localhost:27017/
MONGO_DATABASE=unifi_releases
```

## 使用说明

### 爬虫部分

#### 基本用法

运行爬虫获取产品发布信息：
```bash
python run.py
```

#### 高级选项

可以使用以下参数自定义爬取行为：

- `--limit`：限制爬取的项目数量（默认为0，表示不限制）
```bash
python run.py --limit 100
```

- `--batch-size`：设置每批处理的数量（默认为50）
```bash
python run.py --batch-size 100
```

- `--clean-checkpoint`：清除检查点文件，从头开始爬取
```bash
python run.py --clean-checkpoint
```

### 时间轴生成部分

运行以下命令生成时间轴：

```bash
python generate_timeline.py
```

时间轴具有以下附加功能：
1. **智能产品线分组**：基于预定义映射自动将产品归类至主要产品线
2. **版本类型标签页**：可在同一产品线内按GA/RC等版本类型切换查看
3. **年份折叠分组**：按年份组织版本，可折叠/展开特定年份的发布
4. **统计信息**：显示每个产品线、版本类型、年份的发布数量

### 数据查看

使用MongoDB Compass或其他MongoDB客户端连接到数据库后，可以查看和管理爬取的数据。

连接MongoDB：
- 连接字符串：`mongodb://localhost:27017/`
- 数据库名称：`unifi_releases`
- 集合名称：`releases`

## 数据库备份与恢复

为了方便将数据从本地环境迁移到云服务器或其他部署环境，以下提供了MongoDB数据库的备份和恢复流程。

### 安装MongoDB数据库工具

首先需要安装MongoDB数据库工具（MongoDB Database Tools）：
1. 从[MongoDB官网](https://www.mongodb.com/try/download/database-tools)下载适合你系统的工具
2. 安装工具并确保它们在你的系统路径中

### 备份数据库

使用`mongodump`工具创建数据库备份：

```bash
mongodump --db unifi_releases --out ./backup
```

这将在当前目录的`backup`文件夹中创建数据库的完整备份。

### 数据库恢复

将备份文件传输到目标服务器后，使用`mongorestore`工具恢复数据库：

```bash
mongorestore --db unifi_releases ./backup/unifi_releases
```

### 在不同环境间传输备份

将备份文件从本地传输到云服务器：

```bash
# 使用SCP传输（Linux/Mac/Windows WSL）
scp -r ./backup user@服务器IP:/目标路径

# 或者使用其他文件传输工具如FTP、SFTP等
```

确保目标服务器上已安装并配置好MongoDB服务。

## 项目结构

```
UnifiScrapy/
├── unifi_scraper/           # 爬虫核心模块
│   ├── __init__.py          # 初始化文件
│   ├── models.py            # 数据模型定义
│   ├── storage.py           # 数据库连接和存储逻辑
│   ├── graphql_scraper.py   # GraphQL API爬虫实现
│   └── utils.py             # 工具函数
├── timeline_output/         # 时间轴展示模块
│   └── index.html           # 时间轴生成器
├── run.py                   # 爬虫运行入口
├── generate_timeline.py     # 时间轴生成入口
├── requirements.txt         # 依赖列表
├── .env.example             # 环境变量示例
└── README.md                # 项目说明
```

## 数据模型

系统处理的产品发布信息包含以下主要字段：

- `product_name`：产品名称
- `version`：版本号
- `release_date`：发布日期
- `release_id`：唯一标识符
- `release_notes`：发布说明
- `download_links`：下载链接
- `firmware_type`：固件类型
- `is_beta`：是否为测试版本
- `tags`：标签列表
- `stage`：发布阶段(GA/RC/Beta等)
- `improvements`：改进列表
- `bugfixes`：修复的问题
- `known_issues`：已知问题

## 版本类型说明

时间轴中显示的版本类型包括：
- **GA (General Availability)**: 正式发布版，已完成全面测试并对所有用户开放的稳定版本
- **RC (Release Candidate)**: 发布候选版，即将成为正式版本的预发布版，主要用于最终测试
- **Beta**: 测试版，功能基本完整但可能存在已知或未知问题，用于公开测试
- **Alpha**: 早期测试版，功能不完整且不稳定，通常仅供内部测试

## 产品线分组逻辑

时间轴使用如下逻辑自动确定产品所属产品线：

1. 首先检查`tags`字段中是否包含已知产品线关键词，如"unifi-network"、"unifi-protect"等
2. 如果找不到匹配的标签，则尝试从`product_name`中识别产品线关键词
3. 如果无法确定，则使用第一个标签或默认为"Other"

这种分组机制可以将分散的产品名有效地组织到少量主要产品线类别中，使导航更加清晰。

## 自定义时间轴

如需自定义时间轴外观或功能，可修改以下部分：
1. `ImprovedTimelineGenerator`类中的`create_template_files`方法可修改HTML模板
2. CSS和JavaScript可直接在对应的变量中修改
3. `PRODUCT_LINE_MAPPING`和`PRODUCT_LINE_ORDER`可调整产品线的映射和显示顺序

## 故障排除

### 常见问题

1. **连接MongoDB失败**

   确保MongoDB服务正在运行，并检查`.env`文件中的连接设置。

2. **API请求失败**

   检查网络连接，可能是暂时性网络问题或API限制。

3. **数据不完整**

   某些产品可能缺少特定字段，检查日志获取详细错误信息。

### 日志查看

程序运行日志保存在`unifi_scraper.log`文件中，可查看详细的执行过程和错误信息。

## 贡献指南

欢迎提交问题报告和改进建议！如果您想贡献代码：

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交Pull Request

## 许可证

本项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件。 