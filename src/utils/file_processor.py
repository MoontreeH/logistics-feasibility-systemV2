"""
文件处理器

支持Excel文件上传、解析和数据提取
"""

import pandas as pd
import io
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


class FileProcessor:
    """
    文件处理器
    
    支持：
    - Excel文件 (.xlsx, .xls)
    - CSV文件 (.csv)
    - 文本文件 (.txt)
    """
    
    def __init__(self):
        """初始化文件处理器"""
        self.supported_types = [".xlsx", ".xls", ".csv", ".txt"]
    
    def process_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        处理上传的文件
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
        
        Returns:
            处理结果
        """
        ext = Path(filename).suffix.lower()
        
        if ext not in self.supported_types:
            return {
                "success": False,
                "error": f"不支持的文件类型: {ext}",
                "supported_types": self.supported_types
            }
        
        try:
            if ext in [".xlsx", ".xls"]:
                return self._process_excel(file_content)
            elif ext == ".csv":
                return self._process_csv(file_content)
            elif ext == ".txt":
                return self._process_txt(file_content)
        except Exception as e:
            return {
                "success": False,
                "error": f"处理文件失败: {str(e)}"
            }
    
    def _process_excel(self, file_content: bytes) -> Dict[str, Any]:
        """处理Excel文件"""
        df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        
        # 提取关键信息
        key_info = self._extract_key_info(df)
        
        # 生成预览
        preview = self._generate_preview(df)
        
        return {
            "success": True,
            "data_type": "excel",
            "filename": "excel_file",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview,
            "key_info": key_info,
            "dataframe": df
        }
    
    def _process_csv(self, file_content: bytes) -> Dict[str, Any]:
        """处理CSV文件"""
        df = pd.read_csv(io.BytesIO(file_content))
        
        key_info = self._extract_key_info(df)
        preview = self._generate_preview(df)
        
        return {
            "success": True,
            "data_type": "csv",
            "filename": "csv_file",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview,
            "key_info": key_info,
            "dataframe": df
        }
    
    def _process_txt(self, file_content: bytes) -> Dict[str, Any]:
        """处理文本文件"""
        content = file_content.decode('utf-8')
        
        return {
            "success": True,
            "data_type": "text",
            "filename": "text_file",
            "content": content,
            "preview": content[:500] + "..." if len(content) > 500 else content
        }
    
    def _extract_key_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        从DataFrame中提取关键信息
        
        使用列名匹配和模式识别
        """
        key_info = {
            "has_order_data": False,
            "has_cost_data": False,
            "has_price_data": False,
            "detected_fields": {}
        }
        
        # 关键词映射到字段
        field_keywords = {
            "daily_order_count": ["日订单", "订单量", "日单量", "每天订单", "日均订单"],
            "items_per_order": ["件数", "每单件数", "单均件数", "商品数量"],
            "weight": ["重量", "单重", "公斤", "kg", "weight"],
            "distance": ["距离", "配送距离", "公里", "km", "distance"],
            "purchase_price": ["采购价", "进价", "成本价", "买入价"],
            "selling_price": ["售价", "卖价", "销售价", "零售价"],
            "floor": ["楼层", "上楼", "层数"],
        }
        
        columns_lower = [col.lower() for col in df.columns]
        
        for field, keywords in field_keywords.items():
            for col, col_lower in zip(df.columns, columns_lower):
                for kw in keywords:
                    if kw in col_lower:
                        key_info["detected_fields"][field] = {
                            "column": col,
                            "values": df[col].dropna().tolist()[:10]  # 前10个非空值
                        }
                        break
        
        # 判断数据类型
        if any(k in key_info["detected_fields"] for k in ["daily_order_count", "items_per_order"]):
            key_info["has_order_data"] = True
        
        if any(k in key_info["detected_fields"] for k in ["purchase_price", "selling_price"]):
            key_info["has_price_data"] = True
        
        if "weight" in key_info["detected_fields"] or "distance" in key_info["detected_fields"]:
            key_info["has_cost_data"] = True
        
        return key_info
    
    def _generate_preview(self, df: pd.DataFrame, max_rows: int = 10) -> str:
        """生成数据预览"""
        preview_df = df.head(max_rows)
        
        # 转换为字符串格式
        lines = []
        lines.append("| " + " | ".join(preview_df.columns) + " |")
        lines.append("|" + "|".join(["---"] * len(preview_df.columns)) + "|")
        
        for _, row in preview_df.iterrows():
            values = [str(v)[:20] for v in row.values]  # 限制每列宽度
            lines.append("| " + " | ".join(values) + " |")
        
        if len(df) > max_rows:
            lines.append(f"\n... 共 {len(df)} 行")
        
        return "\n".join(lines)
    
    def extract_for_llm(self, file_result: Dict[str, Any]) -> str:
        """
        提取文件信息供LLM理解
        
        Args:
            file_result: 文件处理结果
        
        Returns:
            LLM友好的描述文本
        """
        if not file_result.get("success"):
            return f"文件处理失败: {file_result.get('error')}"
        
        lines = ["【上传文件分析】"]
        lines.append(f"文件类型: {file_result.get('data_type')}")
        
        if file_result.get("data_type") == "excel":
            lines.append(f"数据量: {file_result.get('row_count')} 行, {file_result.get('column_count')} 列")
            lines.append(f"列名: {', '.join(file_result.get('columns', []))}")
            
            key_info = file_result.get("key_info", {})
            if key_info.get("detected_fields"):
                lines.append("\n识别到的关键字段:")
                for field, info in key_info["detected_fields"].items():
                    sample_values = info.get("values", [])[:5]
                    lines.append(f"  - {field}: 列名「{info['column']}」, 示例值: {sample_values}")
            else:
                lines.append("\n未识别到关键字段，请人工确认。")
        
        elif file_result.get("data_type") == "text":
            lines.append(f"内容预览:\n{file_result.get('preview', '')}")
        
        return "\n".join(lines)


class ExcelImporter:
    """
    Excel数据导入器
    
    专门处理物流业务相关的Excel数据导入
    """
    
    # 标准列名映射
    STANDARD_COLUMNS = {
        "日订单数": "daily_order_count",
        "日均订单": "daily_order_count",
        "订单量": "daily_order_count",
        "件数": "items_per_order",
        "每单件数": "items_per_order",
        "单均件数": "items_per_order",
        "重量": "weight_per_item",
        "单重": "weight_per_item",
        "公斤": "weight_per_item",
        "距离": "distance_km",
        "配送距离": "distance_km",
        "公里": "distance_km",
        "楼层": "floor",
        "上楼": "floor",
        "采购价": "purchase_price",
        "进价": "purchase_price",
        "售价": "selling_price",
        "卖价": "selling_price",
    }
    
    def __init__(self):
        """初始化导入器"""
        self.processor = FileProcessor()
    
    def import_from_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        从文件导入数据
        
        Args:
            file_content: 文件内容
            filename: 文件名
        
        Returns:
            导入结果
        """
        # 处理文件
        result = self.processor.process_file(file_content, filename)
        
        if not result.get("success"):
            return result
        
        # 如果是Excel，尝试标准化列名
        if result.get("data_type") == "excel":
            df = result.get("dataframe")
            if df is not None:
                standardized = self._standardize_columns(df)
                result["standardized_data"] = standardized
                result["import_summary"] = self._generate_import_summary(standardized)
        
        return result
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        standardized = df.copy()
        rename_map = {}
        
        for col in standardized.columns:
            col_lower = col.lower().strip()
            for standard, internal in self.STANDARD_COLUMNS.items():
                if standard in col_lower:
                    rename_map[col] = internal
                    break
        
        standardized = standardized.rename(columns=rename_map)
        return standardized
    
    def _generate_import_summary(self, df: pd.DataFrame) -> str:
        """生成导入摘要"""
        lines = ["【Excel数据导入摘要】"]
        
        # 统计各字段
        field_mapping = {
            "daily_order_count": "日订单数",
            "items_per_order": "件数",
            "weight_per_item": "重量(kg)",
            "distance_km": "距离(km)",
            "floor": "楼层",
            "purchase_price": "采购价",
            "selling_price": "售价",
        }
        
        for internal, display in field_mapping.items():
            if internal in df.columns:
                non_null = df[internal].dropna()
                if len(non_null) > 0:
                    lines.append(f"  - {display}: {len(non_null)} 条数据, "
                               f"范围: {non_null.min():.2f} ~ {non_null.max():.2f}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("文件处理器测试")
    print("="*60)
    
    processor = FileProcessor()
    
    # 模拟Excel数据
    import pandas as pd
    import io
    
    # 创建测试数据
    data = {
        "日订单数": [100, 150, 80, 120, 90],
        "件数": [5, 3, 8, 4, 6],
        "重量(kg)": [10, 5, 15, 8, 12],
        "距离(km)": [20, 15, 25, 18, 22],
        "采购价": [50, 40, 60, 45, 55],
        "售价": [80, 70, 90, 75, 85]
    }
    df = pd.DataFrame(data)
    
    # 保存为Excel
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    
    # 测试处理
    result = processor.process_file(buffer.read(), "test.xlsx")
    
    print(f"处理结果: {result['success']}")
    print(f"数据类型: {result.get('data_type')}")
    print(f"行数: {result.get('row_count')}")
    print(f"\n关键信息:")
    print(result.get('key_info'))
    print(f"\n预览:")
    print(result.get('preview'))
    
    # 测试LLM友好输出
    print("\n【LLM友好描述】")
    llm_text = processor.extract_for_llm(result)
    print(llm_text)
