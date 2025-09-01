"""
配置文件
"""

# 数据库配置
DB_CONFIG = {
    'db_name': '{{ cookiecutter.project_slug }}.db',
    'table_name': '{{ cookiecutter.table_name }}',
    'batch_size': {{ cookiecutter.batch_size }},
    'max_retries': {{ cookiecutter.max_retries }}
}

# 数据源配置
DATA_CONFIG = {
    'data_file': '{{ cookiecutter.data_file }}',
    'data_separator': '{{ cookiecutter.data_separator }}'
}

# 缓存配置
CACHE_CONFIG = {
    'enable': {{ 'True' if cookiecutter.enable_cache == 'y' else 'False' }},
    'size': {{ cookiecutter.cache_size }}
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': '{{ cookiecutter.project_slug }}.log'
}