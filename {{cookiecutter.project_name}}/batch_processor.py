"""
BatchProcessor - 批量数据处理框架

提供标准化的数据导入、批处理、结果回填流程模板
"""

import pandas as pd
import sqlite3
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
from cachetools import cached, LRUCache
import logging
from datetime import datetime


class BatchProcessor(ABC):
    """
    批量数据处理抽象基类
    
    标准流程:
    1. 导入数据到SQLite
    2. 批量处理未处理的数据 
    3. 执行业务逻辑并回填结果
    """
    
    def __init__(self, 
                 batch_size: int = 100,
                 table_name: str = 'batch_table',
                 db_name: str = 'batch_data.db',
                 cursor_field: str = 'id',
                 status_field: str = 'is_processed',
                 retry_field: str = 'retry_count',
                 max_retries: int = 3):
        """
        初始化批处理器
        
        Args:
            batch_size: 每批处理的数据量
            table_name: 数据表名
            db_name: SQLite数据库名
            cursor_field: 游标字段名
            status_field: 处理状态字段名  
            retry_field: 重试次数字段名
            max_retries: 最大重试次数
        """
        self.batch_size = batch_size
        self.table_name = table_name
        self.db_name = db_name
        self.cursor_field = cursor_field
        self.status_field = status_field
        self.retry_field = retry_field
        self.max_retries = max_retries
        
        # 初始化数据库连接
        self.conn = sqlite3.connect(self.db_name)
        
        # 设置日志
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def get_data_source(self) -> Union[str, pd.DataFrame]:
        """
        获取数据源
        
        Returns:
            数据源路径(CSV文件路径)或DataFrame对象
        """
        pass
    
    @abstractmethod
    def define_schema(self) -> Dict[str, List[str]]:
        """
        定义表结构
        
        Returns:
            字段定义字典，格式:
            {
                'control_fields': ['is_processed', 'retry_count', ...],
                'result_fields': ['result1', 'result2', ...]
            }
        """
        pass
    
    def fetch_external_data(self, batch_data: pd.DataFrame) -> Dict[str, Any]:
        """
        获取外部数据(如API调用) - 示例方法，可选实现
        
        这是一个示例方法，展示如何在批处理中调用外部API。
        如果你的业务逻辑需要调用外部API，可以重写此方法。
        
        Args:
            batch_data: 当前批次的数据
            
        Returns:
            外部数据字典
            
        示例:
            # 缓存应该用在具体的API调用方法上，而不是这个方法
            @cached(LRUCache(maxsize=1000))
            def _fetch_api_data(self, query_param_tuple):
                # 将查询参数转换为元组以支持缓存
                query_list = list(query_param_tuple)
                # 实现具体的API调用逻辑
                return api_response_data
                
            def fetch_external_data(self, batch_data: pd.DataFrame):
                query_params = batch_data['some_field'].unique().tolist()
                return self._fetch_api_data(tuple(query_params))
        """
        return {}
    
    @abstractmethod
    def process_business_logic(self, batch_data: pd.DataFrame) -> pd.DataFrame:
        """
        处理业务逻辑 - 批量处理
        
        Args:
            batch_data: 当前批次的数据DataFrame
            
        Returns:
            处理后的DataFrame，必须包含:
            - 原始数据的所有列
            - 结果字段的值
            - 保持原有的行顺序和索引
        
        示例:
            def process_business_logic(self, batch_data: pd.DataFrame) -> pd.DataFrame:
                # 如果需要调用外部API
                external_data = self.fetch_external_data(batch_data)
                
                # 处理每一行或批量处理
                for idx, row in batch_data.iterrows():
                    # 执行业务逻辑
                    batch_data.loc[idx, 'result1'] = some_calculation(row)
                    batch_data.loc[idx, 'result2'] = some_other_logic(row)
                
                return batch_data
        """
        pass
    
    def import_data(self) -> int:
        """
        导入数据到SQLite
        
        Returns:
            导入的数据行数
        """
        self.logger.info("开始导入数据...")
        
        # 获取数据源
        data_source = self.get_data_source()
        
        if isinstance(data_source, str):
            # 从文件读取
            if data_source.endswith('.csv'):
                df = pd.read_csv(data_source, sep='\t')
            elif data_source.endswith('.xlsx'):
                df = pd.read_excel(data_source)
            else:
                raise ValueError(f"不支持的文件格式: {data_source}")
        elif isinstance(data_source, pd.DataFrame):
            df = data_source.copy()
        else:
            raise ValueError("数据源必须是文件路径或DataFrame对象")
        
        # 添加控制字段和结果字段
        schema = self.define_schema()
        
        # 添加控制字段
        for field in schema.get('control_fields', []):
            if field == self.status_field:
                df[field] = False
            elif field == self.retry_field:
                df[field] = 0
            else:
                df[field] = None
        
        # 添加结果字段
        for field in schema.get('result_fields', []):
            df[field] = ''
        
        # 导入到SQLite
        row_count = len(df)
        df.to_sql(self.table_name, self.conn, if_exists='replace', index=False)
        
        self.logger.info(f"数据导入完成，共{row_count}条记录")
        return row_count
    
    def process_batches(self, debug_batch_times: Optional[int] = None) -> int:
        """
        批量处理数据
        
        Args:
            debug_batch_times: 调试模式下只处理指定数量的批次，None表示处理所有数据
            
        Returns:
            处理的总记录数
        """
        cursor_id = 0
        total_processed = 0
        batch_count = 0
        
        if debug_batch_times:
            self.logger.info(f"开始批量处理 (调试模式: 限制{debug_batch_times}个批次)...")
        else:
            self.logger.info("开始批量处理...")
        
        while True:
            # 检查是否达到调试批次限制
            if debug_batch_times and batch_count >= debug_batch_times:
                self.logger.info(f"已达到调试批次限制({debug_batch_times}个批次)，停止处理")
                break
                
            # 查询未处理的数据批次
            batch_df = self._get_next_batch(cursor_id)
            
            if batch_df.empty:
                self.logger.info("没有更多数据需要处理")
                break
            
            try:
                batch_count += 1
                # 处理当前批次
                processed_count = self._process_single_batch(batch_df)
                total_processed += processed_count
                
                # 更新游标
                cursor_id = batch_df[self.cursor_field].iloc[-1]
                
                if debug_batch_times:
                    self.logger.info(f"已处理第{batch_count}个批次，共{processed_count}条数据, 当前游标ID为{cursor_id}")
                else:
                    self.logger.info(f"已处理{total_processed}条数据, 当前游标ID为{cursor_id}")
                
            except Exception as e:
                self.logger.error(f"处理批次时发生错误: {str(e)}")
                # 可以选择继续处理下一批次或停止
                cursor_id = batch_df[self.cursor_field].iloc[-1]
                batch_count += 1  # 错误的批次也要计数
                continue
        
        if debug_batch_times:
            self.logger.info(f"调试批量处理完成，处理了{batch_count}个批次，总共{total_processed}条记录")
        else:
            self.logger.info(f"批量处理完成，总共处理{total_processed}条记录")
        return total_processed
    
    def _get_next_batch(self, cursor_id: int) -> pd.DataFrame:
        """获取下一批待处理数据"""
        query = f"""
        SELECT *
        FROM {self.table_name}
        WHERE {self.cursor_field} > {cursor_id}
        AND ({self.status_field} = 0 OR {self.status_field} IS FALSE)
        AND {self.retry_field} < {self.max_retries}
        ORDER BY {self.cursor_field}
        LIMIT {self.batch_size}
        """
        
        return pd.read_sql(query, self.conn)
    
    def _process_single_batch(self, batch_df: pd.DataFrame) -> int:
        """处理单个批次的数据"""
        try:
            # 执行批量业务逻辑处理
            processed_df = self.process_business_logic(batch_df.copy())
            
            # 准备更新记录
            updates = []
            schema = self.define_schema()
            result_fields = schema.get('result_fields', [])
            
            for idx, row in batch_df.iterrows():
                try:
                    # 获取处理后的结果
                    processed_row = processed_df.loc[idx]
                    
                    # 构建更新记录: [is_processed, result_field1, result_field2, ..., retry_count, id]
                    update_record = [True]  # is_processed = True
                    
                    # 添加结果字段值
                    for field in result_fields:
                        value = processed_row.get(field, '')
                        # 确保值不是NaN
                        if pd.isna(value):
                            value = ''
                        update_record.append(value)
                    
                    # 添加重试次数和ID
                    update_record.append(row[self.retry_field])  # retry_count保持不变
                    update_record.append(row[self.cursor_field])  # WHERE条件的ID
                    
                    updates.append(update_record)
                    
                except Exception as e:
                    self.logger.error(f"处理行{row[self.cursor_field]}时出错: {str(e)}")
                    # 增加重试次数，结果字段设为空
                    retry_count = row[self.retry_field] + 1
                    update_record = [False] + [''] * len(result_fields) + [retry_count, row[self.cursor_field]]
                    updates.append(update_record)
            
            # 批量更新数据库
            if updates:
                self._batch_update(updates)
            
            return len(updates)
            
        except Exception as e:
            self.logger.error(f"处理批次时发生错误: {str(e)}")
            raise
    
    def _get_update_fields(self) -> List[str]:
        """获取需要更新的字段列表"""
        schema = self.define_schema()
        fields = [self.status_field]
        fields.extend(schema.get('result_fields', []))
        fields.append(self.retry_field)
        return fields
    
    def _batch_update(self, updates: List[List]):
        """批量更新数据库"""
        update_fields = self._get_update_fields()
        placeholders = ', '.join([f"{field} = ?" for field in update_fields])
        
        update_sql = f"""
        UPDATE {self.table_name}
        SET {placeholders}
        WHERE {self.cursor_field} = ?
        """
        
        cursor = self.conn.cursor()
        cursor.executemany(update_sql, updates)
        self.conn.commit()
    
    def get_statistics(self) -> Dict[str, int]:
        """获取处理统计信息"""
        stats_query = f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN {self.status_field} = 1 THEN 1 ELSE 0 END) as processed,
            SUM(CASE WHEN {self.status_field} = 0 AND {self.retry_field} < {self.max_retries} THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN {self.retry_field} >= {self.max_retries} THEN 1 ELSE 0 END) as failed
        FROM {self.table_name}
        """
        
        result = pd.read_sql(stats_query, self.conn)
        return result.iloc[0].to_dict()
    
    def export_results(self, output_path: str, only_processed: bool = True):
        """导出处理结果"""
        if only_processed:
            query = f"SELECT * FROM {self.table_name} WHERE {self.status_field} = 1"
        else:
            query = f"SELECT * FROM {self.table_name}"
        
        df = pd.read_sql(query, self.conn)
        
        if output_path.endswith('.csv'):
            df.to_csv(output_path, index=False, sep='\t')
        elif output_path.endswith('.xlsx'):
            df.to_excel(output_path, index=False)
        else:
            raise ValueError("输出文件格式必须是CSV或Excel")
        
        self.logger.info(f"结果已导出到: {output_path}")
    
    def run(self, debug_batch_times: Optional[int] = None):
        """
        运行完整的批处理流程
        
        Args:
            debug_batch_times: 调试模式下只处理指定数量的批次，None表示处理所有数据
        """
        start_time = datetime.now()
        if debug_batch_times:
            self.logger.info(f"开始执行批处理任务 (调试模式: 只处理{debug_batch_times}个批次)...")
        else:
            self.logger.info("开始执行批处理任务...")
        
        try:
            # 导入数据
            import_count = self.import_data()
            
            # 处理数据
            process_count = self.process_batches(debug_batch_times)
            
            # 输出统计信息
            stats = self.get_statistics()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info("=" * 50)
            if debug_batch_times:
                self.logger.info(f"调试批处理完成! (处理了{debug_batch_times}个批次)")
            else:
                self.logger.info("批处理任务完成!")
            self.logger.info(f"总耗时: {duration:.2f}秒")
            self.logger.info(f"导入记录: {import_count}")
            self.logger.info(f"处理记录: {process_count}")
            self.logger.info(f"成功处理: {stats['processed']}")
            self.logger.info(f"等待处理: {stats['pending']}")
            self.logger.info(f"处理失败: {stats['failed']}")
            if debug_batch_times:
                remaining = stats['total'] - stats['processed'] - stats['failed']
                self.logger.info(f"剩余未处理: {remaining}")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"批处理任务失败: {str(e)}")
            raise
        
        finally:
            # 关闭数据库连接
            if hasattr(self, 'conn'):
                self.conn.close()