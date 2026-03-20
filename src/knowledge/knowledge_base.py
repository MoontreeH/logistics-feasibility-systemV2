"""
知识库模块

管理行业知识、最佳实践和案例
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class KnowledgeItem:
    """知识项"""
    id: str
    category: str  # industry_benchmark, best_practice, risk_case, optimization_tip
    title: str
    content: str
    source: str
    business_type: Optional[str]  # tob_enterprise, meal_delivery, or None (通用)
    tags: List[str]
    created_at: str
    updated_at: str
    usage_count: int = 0


class KnowledgeBase:
    """
    知识库
    
    管理行业知识和最佳实践
    """
    
    def __init__(self, storage_path: str = None):
        """
        初始化知识库
        
        Args:
            storage_path: 存储路径
        """
        if storage_path is None:
            storage_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base"
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.knowledge_file = self.storage_path / "knowledge.json"
        self.knowledge: Dict[str, KnowledgeItem] = {}
        
        self._load_knowledge()
        self._init_default_knowledge()
    
    def _load_knowledge(self):
        """加载知识库"""
        if self.knowledge_file.exists():
            try:
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item_id, item_data in data.items():
                        self.knowledge[item_id] = KnowledgeItem(**item_data)
            except Exception as e:
                print(f"加载知识库失败: {e}")
    
    def _save_knowledge(self):
        """保存知识库"""
        try:
            data = {k: asdict(v) for k, v in self.knowledge.items()}
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存知识库失败: {e}")
    
    def _init_default_knowledge(self):
        """初始化默认知识"""
        if self.knowledge:
            return
        
        default_knowledge = [
            # 行业基准
            KnowledgeItem(
                id="benchmark_tob_cost_per_order",
                category="industry_benchmark",
                title="TOB企业购单均成本基准",
                content="TOB企业购行业平均单均成本为50-80元，其中：订单处理占15-20%，运输配送占30-40%，末端交付占20-30%",
                source="行业调研数据",
                business_type="tob_enterprise",
                tags=["成本基准", "TOB", "单均成本"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            KnowledgeItem(
                id="benchmark_meal_cost_per_order",
                category="industry_benchmark",
                title="餐配业务单均成本基准",
                content="餐配业务行业平均单均成本为80-120元，其中：冷链成本占20-30%，运输配送占25-35%，库存持有占15-25%",
                source="行业调研数据",
                business_type="meal_delivery",
                tags=["成本基准", "餐配", "单均成本", "冷链"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            
            # 最佳实践
            KnowledgeItem(
                id="practice_route_optimization",
                category="best_practice",
                title="配送路线优化最佳实践",
                content="通过TMS系统优化配送路线，可减少10-15%的运输成本。关键措施：1)合并相近区域订单；2)设置合理时间窗口；3)提高装载率至85%以上",
                source="物流优化案例库",
                business_type=None,
                tags=["运输优化", "路线规划", "降本"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            KnowledgeItem(
                id="practice_inventory_turnover",
                category="best_practice",
                title="库存周转率提升方法",
                content="将库存周转天数从7天降至5天，可减少25%的库存持有成本。方法：1)实施JIT配送；2)优化安全库存；3)提高需求预测准确性",
                source="仓储管理最佳实践",
                business_type=None,
                tags=["库存优化", "周转率", "JIT"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            
            # 风险案例
            KnowledgeItem(
                id="risk_upstairs_delivery",
                category="risk_case",
                title="上楼配送成本风险",
                content="某企业客户案例中，上楼配送占总成本的35%，其中无电梯楼宇的单均成本比有电梯楼宇高60%。建议：协商楼下交货或收取上楼费",
                source="实际案例分析",
                business_type="tob_enterprise",
                tags=["风险", "上楼", "末端交付"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            KnowledgeItem(
                id="risk_cold_chain_break",
                category="risk_case",
                title="冷链断链风险",
                content="餐配业务中，冷链断链导致的损耗率高达8-12%。全程温度监控可将损耗率降至3%以下。关键控制点：装车、运输、卸货",
                source="质量管理案例",
                business_type="meal_delivery",
                tags=["风险", "冷链", "损耗", "温控"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            
            # 优化技巧
            KnowledgeItem(
                id="tip_batch_processing",
                category="optimization_tip",
                title="批量处理降本技巧",
                content="推行波次拣选和批量订单处理，可将订单处理效率提升20%，人均处理行数从1000行/天提升至1200行/天",
                source="运营优化经验",
                business_type=None,
                tags=["效率", "批量处理", "拣选"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            KnowledgeItem(
                id="tip_consolidation",
                category="optimization_tip",
                title="订单合并策略",
                content="将同一客户的多张小单合并为一张大单配送，可减少30%的配送成本。建议设置最低起送量门槛",
                source="配送优化案例",
                business_type=None,
                tags=["合并", "配送", "成本"],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
        ]
        
        for item in default_knowledge:
            self.knowledge[item.id] = item
        
        self._save_knowledge()
    
    def add_knowledge(self, item: KnowledgeItem) -> str:
        """
        添加知识项
        
        Args:
            item: 知识项
        
        Returns:
            知识项ID
        """
        if not item.id:
            item.id = f"knowledge_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        item.updated_at = datetime.now().isoformat()
        self.knowledge[item.id] = item
        self._save_knowledge()
        
        return item.id
    
    def get_knowledge(self, item_id: str) -> Optional[KnowledgeItem]:
        """
        获取知识项
        
        Args:
            item_id: 知识项ID
        
        Returns:
            知识项
        """
        item = self.knowledge.get(item_id)
        if item:
            item.usage_count += 1
            self._save_knowledge()
        return item
    
    def search_knowledge(
        self, 
        category: str = None, 
        business_type: str = None,
        tags: List[str] = None,
        keyword: str = None
    ) -> List[KnowledgeItem]:
        """
        搜索知识项
        
        Args:
            category: 类别筛选
            business_type: 业务类型筛选
            tags: 标签筛选
            keyword: 关键词搜索
        
        Returns:
            知识项列表
        """
        results = []
        
        for item in self.knowledge.values():
            # 类别筛选
            if category and item.category != category:
                continue
            
            # 业务类型筛选
            if business_type and item.business_type and item.business_type != business_type:
                continue
            
            # 标签筛选
            if tags and not any(tag in item.tags for tag in tags):
                continue
            
            # 关键词搜索
            if keyword:
                keyword_lower = keyword.lower()
                if (keyword_lower not in item.title.lower() and 
                    keyword_lower not in item.content.lower() and
                    keyword_lower not in ','.join(item.tags).lower()):
                    continue
            
            results.append(item)
        
        # 按使用次数排序
        results.sort(key=lambda x: x.usage_count, reverse=True)
        
        return results
    
    def get_relevant_knowledge(
        self, 
        business_type: str, 
        cost_structure: Dict[str, float]
    ) -> List[KnowledgeItem]:
        """
        获取相关知识（基于成本结构）
        
        Args:
            business_type: 业务类型
            cost_structure: 成本结构
        
        Returns:
            相关知识列表
        """
        relevant_items = []
        
        # 根据成本结构识别高成本环节
        high_cost_categories = [
            cat for cat, pct in cost_structure.items() 
            if pct > 25
        ]
        
        # 搜索相关知识
        for category in high_cost_categories:
            # 映射成本类别到标签
            tag_mapping = {
                "运输配送": ["运输", "配送"],
                "末端交付": ["上楼", "末端"],
                "库存持有": ["库存", "周转率"],
                "订单处理": ["订单", "处理"],
            }
            
            tags = tag_mapping.get(category, [category])
            
            items = self.search_knowledge(
                business_type=business_type,
                tags=tags
            )
            
            relevant_items.extend(items)
        
        # 去重并排序
        seen_ids = set()
        unique_items = []
        for item in relevant_items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_items.append(item)
        
        return unique_items[:5]  # 返回前5条
    
    def update_knowledge(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新知识项
        
        Args:
            item_id: 知识项ID
            updates: 更新内容
        
        Returns:
            是否成功
        """
        if item_id not in self.knowledge:
            return False
        
        item = self.knowledge[item_id]
        
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        item.updated_at = datetime.now().isoformat()
        self._save_knowledge()
        
        return True
    
    def delete_knowledge(self, item_id: str) -> bool:
        """
        删除知识项
        
        Args:
            item_id: 知识项ID
        
        Returns:
            是否成功
        """
        if item_id not in self.knowledge:
            return False
        
        del self.knowledge[item_id]
        self._save_knowledge()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计
        
        Returns:
            统计信息
        """
        categories = {}
        for item in self.knowledge.values():
            categories[item.category] = categories.get(item.category, 0) + 1
        
        return {
            "total_items": len(self.knowledge),
            "categories": categories,
            "most_used": sorted(
                self.knowledge.values(), 
                key=lambda x: x.usage_count, 
                reverse=True
            )[:5]
        }


if __name__ == "__main__":
    # 测试知识库
    kb = KnowledgeBase()
    
    print("="*60)
    print("知识库测试")
    print("="*60)
    
    # 统计
    stats = kb.get_stats()
    print(f"\n知识库统计:")
    print(f"  总条目数: {stats['total_items']}")
    print(f"  分类分布: {stats['categories']}")
    
    # 搜索
    print(f"\n搜索'运输'相关知识:")
    results = kb.search_knowledge(keyword="运输")
    for item in results:
        print(f"  • {item.title} ({item.category})")
    
    # 获取相关知识
    print(f"\nTOB业务相关知识:")
    cost_structure = {"运输配送": 35, "末端交付": 30}
    relevant = kb.get_relevant_knowledge("tob_enterprise", cost_structure)
    for item in relevant:
        print(f"  • {item.title}")
