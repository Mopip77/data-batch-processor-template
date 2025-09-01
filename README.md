# Data Batch Processor Template

一个用于快速创建批量数据处理脚本的Cookiecutter模板，专为Python + Jupyter环境设计。

## 特性

- 🏗️ **标准化流程**: 数据导入 → 批处理 → 结果回填的固定模式
- 🔄 **断点续传**: 基于游标ID实现处理中断后继续
- 🔁 **自动重试**: 失败记录自动重试机制
- 📈 **进度跟踪**: 实时显示处理进度和统计信息
- 💾 **缓存支持**: 可选的API调用缓存，避免重复请求
- 📊 **结果导出**: 支持CSV/Excel格式结果导出
- 🛠️ **高度可配置**: 批次大小、重试次数、超时设置等

## 快速使用

### 1. 安装Cookiecutter

```bash
pip install cookiecutter
```

### 2. 创建新项目

```bash
# 使用本地模板
cookiecutter ./data-batch-processor-template

# 或使用Git仓库(如果已推送)
# cookiecutter https://github.com/Mopip77/data-batch-processor-template
```

### 3. 按提示配置项目

```
project_name [my-batch-task]: 我的数据处理任务
description [批量数据处理项目]: 订单业绩归因批量处理
author_name [Your Name]: 张三
data_file [data.csv]: orders.csv
batch_size [100]: 50
enable_cache [y]: y
...
```

### 4. 进入项目并开始开发

```bash
cd 我的数据处理任务
jupyter lab main.ipynb
```

### 5. 修改业务逻辑

只需实现4个核心方法：

```python
class MyProcessor(BatchProcessor):
    def get_data_source(self):
        return 'data.csv'  # 数据源
    
    def define_schema(self):
        return {
            'control_fields': ['is_processed', 'retry_count'],
            'result_fields': ['result1', 'result2']  # 你的结果字段
        }
    
    def fetch_external_data(self, batch_data):
        # 实现API调用逻辑
        pass
    
    def process_business_logic(self, row, external_data):
        # 实现核心业务逻辑
        return {'result1': 'value1', 'result2': 'value2'}
```

## 项目结构

生成的项目结构：

```
your-project-name/
├── batch_processor.py    # 核心框架代码
├── config.py            # 配置文件
├── main.ipynb           # 主要工作文件(需要修改)
├── example.ipynb        # 完整示例
├── requirements.txt     # 依赖包
└── README.md           # 项目说明
```

## 适用场景

- 🔄 **批量数据同步**: 定期从外部系统同步数据
- 📊 **数据处理分析**: 对大量数据进行统计、计算、清洗
- 🔍 **数据比对验证**: 多数据源的数据一致性检查
- 📈 **业务数据处理**: 订单处理、用户数据更新等
- 🏷️ **数据标注**: 批量为数据打标签或分类

## 示例用法

参考生成项目中的 `example.ipynb`，包含完整的业绩归因判断示例：

- 从CSV导入订单数据
- 批量调用订单归因API
- 查询员工信息API
- 执行业绩匹配判断
- 输出处理结果和统计

## 框架优势

### 对比传统脚本

| 特性 | 传统脚本 | BatchProcessor框架 |
|------|---------|-------------------|
| 断点续传 | ❌ 需手动实现 | ✅ 内置支持 |
| 错误处理 | ❌ 容易遗漏 | ✅ 统一处理 |
| 进度跟踪 | ❌ 需手动添加 | ✅ 自动显示 |
| 结果导出 | ❌ 需单独编写 | ✅ 一键导出 |
| 配置管理 | ❌ 硬编码参数 | ✅ 统一配置 |
| 代码复用 | ❌ 重复造轮子 | ✅ 专注业务逻辑 |

### 开发效率提升

- **减少80%重复代码**: 只需实现核心业务逻辑
- **标准化流程**: 统一的处理模式，降低出错率
- **开箱即用**: 5分钟创建项目，立即开始开发
- **最佳实践**: 内置缓存、重试、日志等最佳实践

## 贡献

欢迎提交Issue和Pull Request来改进这个模板。

## 许可证

MIT License