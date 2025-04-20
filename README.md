# UnifiScrapy

使用GraphQL API爬取Ubiquiti产品发布信息并存储到MongoDB数据库的Python爬虫项目。

## 项目简介

UnifiScrapy是一个专门设计用于获取Ubiquiti产品发布信息的爬虫工具，通过GraphQL API获取最新的产品版本信息，并将其保存至MongoDB数据库以便进行跟踪和分析。

该项目主要特点：
- 使用GraphQL API获取数据，无需浏览器自动化
- 增量更新机制，避免重复处理
- 断点续传功能，支持中断后继续爬取
- 完整的错误处理和日志记录
- 可配置的参数和灵活的扩展性

## 环境要求

- Python 3.8+
- MongoDB 4.0+
- 网络连接

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

### 基本用法

运行爬虫获取产品发布信息：
```bash
python run.py
```

### 高级选项

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

### 数据查看

使用MongoDB Compass或其他MongoDB客户端连接到数据库后，可以查看和管理爬取的数据。

连接MongoDB：
- 连接字符串：`mongodb://localhost:27017/`
- 数据库名称：`unifi_releases`
- 集合名称：`releases`

## 项目结构

```
UnifiScrapy/
├── unifi_scraper/           # 核心模块
│   ├── __init__.py          # 初始化文件
│   ├── models.py            # 数据模型定义
│   ├── storage.py           # 数据库连接和存储逻辑
│   ├── graphql_scraper.py   # GraphQL API爬虫实现
│   └── utils.py             # 工具函数
├── run.py                   # 运行入口
├── requirements.txt         # 依赖列表
├── .env.example             # 环境变量示例
└── README.md                # 项目说明
```

## 数据模型

爬取的产品发布信息包含以下主要字段：

- `product_name`：产品名称
- `version`：版本号
- `release_date`：发布日期
- `release_id`：唯一标识符
- `release_notes`：发布说明
- `download_links`：下载链接
- `firmware_type`：固件类型
- `is_beta`：是否为测试版本
- `tags`：标签列表
- `improvements`：改进列表
- `bugfixes`：修复的问题
- `known_issues`：已知问题

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