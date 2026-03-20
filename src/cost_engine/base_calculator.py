"""
基础成本计算器

定义成本计算器的基类和通用逻辑
"""

import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class BaseCostCalculator(ABC):
    """成本计算器基类"""
    
    def __init__(self, rates_config_path: str = None):
        """
        初始化计算器
        
        Args:
            rates_config_path: 费率配置文件路径，默认为config/rates.yaml
        """
        if rates_config_path is None:
            # 获取项目根目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            rates_config_path = project_root / "config" / "rates.yaml"
        
        self.rates = self._load_rates(rates_config_path)
    
    def _load_rates(self, config_path: str) -> Dict[str, Any]:
        """加载费率配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_rate(self, category: str, item: str, default: float = 0.0) -> float:
        """
        获取指定费率
        
        Args:
            category: 费率类别（如：order_processing, transportation等）
            item: 费率项目（如：per_line, normal_vehicle_variable等）
            default: 默认值
        
        Returns:
            费率值
        """
        try:
            return self.rates[category][item]['rate']
        except (KeyError, TypeError):
            return default
    
    def get_rate_with_business_type(self, category: str, item: str, 
                                     business_type: str, default: float = 0.0) -> float:
        """
        根据业务类型获取费率
        
        Args:
            category: 费率类别
            item: 费率项目
            business_type: 业务类型（tob_enterprise/meal_delivery）
            default: 默认值
        
        Returns:
            费率值
        """
        try:
            rate_config = self.rates[category][item]
            # 尝试获取业务类型特定的费率
            rate_key = f"rate_{business_type}"
            if rate_key in rate_config:
                return rate_config[rate_key]
            return rate_config.get('rate', default)
        except (KeyError, TypeError):
            return default
    
    @abstractmethod
    def calculate(self, params) -> float:
        """
        计算成本
        
        Args:
            params: 成本参数
        
        Returns:
            成本金额
        """
        pass
