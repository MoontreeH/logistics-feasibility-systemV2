"""
成本环节识别器

使用LLM识别用户输入中涉及的成本环节，并判断数据可用性
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from ..models.cost_link_config import CostLinkConfig, CostLinkInfo, CostLinkType


class CostLinkIdentifier:
    """
    成本环节识别器
    
    识别用户描述中涉及的成本环节，判断哪些环节有数据、哪些没有
    """
    
    # 环节关键词映射
    LINK_KEYWORDS = {
        "order_processing": ["订单", "处理", "系统", "单据", "录入", "审核"],
        "inventory_holding": ["库存", "仓储", "存储", "仓库", "租金", "资金占用"],
        "picking": ["拣选", "拣货", "分拣", "配货", "复核"],
        "packaging": ["包装", "打包", "包材", "装箱"],
        "processing": ["加工", "切配", "预处理", "制作", "组装"],
        "loading": ["装车", "集货", "装载", "搬运", "装货"],
        "transportation": ["运输", "配送", "干线", "车辆", "运费", "里程"],
        "delivery": ["交付", "送货", "上楼", "卸货", "末端", "签收", "等待"],
        "reverse_logistics": ["退货", "逆向", "返品", "召回", "售后"],
        "overhead": ["管理", "间接", "人工", "水电", "系统", "IT"],
    }
    
    def __init__(self, llm_client=None):
        """
        初始化环节识别器
        
        Args:
            llm_client: LLM客户端，用于调用大模型
        """
        self.llm_client = llm_client
    
    def identify_from_text(self, user_input: str, business_type: str) -> CostLinkConfig:
        """
        从用户输入中识别成本环节
        
        Args:
            user_input: 用户输入文本
            business_type: 业务类型
        
        Returns:
            成本环节配置
        """
        # 创建基础配置
        config = CostLinkConfig.create_for_business_type(business_type)
        
        # 基于关键词进行初步识别
        self._identify_by_keywords(config, user_input)
        
        # 如果有LLM客户端，使用LLM进行更精确的识别
        if self.llm_client:
            self._identify_by_llm(config, user_input, business_type)
        
        return config
    
    def _identify_by_keywords(self, config: CostLinkConfig, user_input: str):
        """基于关键词识别环节"""
        user_input_lower = user_input.lower()
        
        for link_name_en, keywords in self.LINK_KEYWORDS.items():
            link = config.get_link_by_name(link_name_en)
            if link:
                # 检查是否提到该环节
                mentioned = any(kw in user_input_lower for kw in keywords)
                if mentioned:
                    link.data_status = "available"
                    link.data_source = "用户输入"
    
    def _identify_by_llm(self, config: CostLinkConfig, user_input: str, business_type: str):
        """使用LLM识别环节"""
        try:
            prompt = self._build_identification_prompt(user_input, business_type)
            response = self.llm_client.chat_completion(
                system_prompt="你是一个物流成本分析专家，擅长识别业务描述中的成本环节。",
                user_prompt=prompt,
                temperature=0.3
            )
            
            # 解析LLM响应
            self._parse_llm_response(config, response)
            
        except Exception as e:
            # LLM识别失败时，保持关键词识别结果
            print(f"LLM环节识别失败: {e}")
    
    def _build_identification_prompt(self, user_input: str, business_type: str) -> str:
        """构建识别提示词"""
        return f"""请分析以下物流业务描述，识别其中涉及的成本环节。

业务类型: {business_type}
业务描述: {user_input}

物流成本环节包括：
1. 订单处理 - 订单接收、系统处理、单据打印等
2. 库存持有 - 库存存储、资金占用、仓储租金等
3. 拣选作业 - 商品拣选、复核、集货等
4. 包装 - 包装材料、包装作业
5. 加工 - 商品加工、分拣、组装（仅餐配业务）
6. 集货装车 - 货物集货、装车作业
7. 运输配送 - 干线运输、配送运输
8. 末端交付 - 卸货、上楼、等待签收等
9. 逆向处理 - 退货处理、检验、报废
10. 管理及间接费用 - 管理人员、IT系统、水电等

请按以下JSON格式返回分析结果：
{{
    "identified_links": [
        {{
            "link_name": "环节名称",
            "has_data": true/false,
            "confidence": "high/medium/low",
            "reason": "判断理由"
        }}
    ],
    "uncertain_links": ["数据状态不明的环节名称"],
    "not_applicable_links": ["不适用于该业务的环节名称"]
}}

注意：
- has_data: 用户描述中是否提供了该环节的相关数据或明确提到
- confidence: 你对判断的置信度
- 如果某个环节用户明确说不需要或业务明显不涉及，请放入not_applicable_links
"""
    
    def _parse_llm_response(self, config: CostLinkConfig, response: str):
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            json_str = self._extract_json(response)
            result = json.loads(json_str)
            
            # 处理识别到的环节
            for link_info in result.get("identified_links", []):
                link_name = link_info.get("link_name", "")
                has_data = link_info.get("has_data", False)
                
                link = config.get_link_by_name(link_name)
                if link:
                    if has_data:
                        link.data_status = "available"
                    else:
                        link.data_status = "unknown"
                    link.data_source = f"LLM识别({link_info.get('confidence', 'medium')})"
            
            # 处理不确定的环节
            for link_name in result.get("uncertain_links", []):
                link = config.get_link_by_name(link_name)
                if link and link.data_status == "unknown":
                    link.data_status = "unknown"
            
            # 处理不适用的环节
            for link_name in result.get("not_applicable_links", []):
                link = config.get_link_by_name(link_name)
                if link:
                    link.is_active = False
                    link.data_status = "not_applicable"
                    
        except Exception as e:
            print(f"解析LLM响应失败: {e}")
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        # 尝试找到JSON块
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        return text
    
    def analyze_custom_link(self, user_description: str) -> Optional[Dict[str, Any]]:
        """
        分析用户描述的自定义环节
        
        Args:
            user_description: 用户对额外环节的描述
        
        Returns:
            自定义环节信息，如果无法解析则返回None
        """
        if not self.llm_client:
            return None
        
        try:
            prompt = f"""用户描述了一个额外的成本环节，请分析并提取关键信息。

用户描述: {user_description}

请按以下JSON格式返回：
{{
    "link_name": "环节名称（简洁）",
    "description": "环节描述",
    "calculation_method": "计算方式描述",
    "cost_driver": "费用产生的动因",
    "can_merge_with_base": true/false,
    "suggested_merge_target": "建议合并到哪个基础环节（如果可以合并）",
    "estimated_rate": "预估费率（如果有）",
    "unit": "计量单位"
}}

分析要点：
1. 这个环节是否可以合并到9大基础环节中计算？
2. 如果不能合并，应该如何独立计算？
3. 费用产生的核心动因是什么？
"""
            
            response = self.llm_client.chat_completion(
                system_prompt="你是一个物流成本分析专家，擅长分析成本构成。",
                user_prompt=prompt,
                temperature=0.3
            )
            
            json_str = self._extract_json(response)
            return json.loads(json_str)
            
        except Exception as e:
            print(f"分析自定义环节失败: {e}")
            return None
    
    def generate_confirmation_questions(self, config: CostLinkConfig) -> List[Dict[str, Any]]:
        """
        生成需要向用户确认的问题
        
        Args:
            config: 成本环节配置
        
        Returns:
            问题列表
        """
        questions = []
        
        # 获取需要确认的环节
        uncertain_links = config.get_links_needing_confirmation()
        
        for link in uncertain_links:
            question = {
                "link_name": link.name,
                "question": f"该业务是否涉及【{link.name}】环节？",
                "description": link.description,
                "options": [
                    {"value": "yes", "label": "是，需要计算该环节成本"},
                    {"value": "no", "label": "否，该环节不涉及"},
                    {"value": "unknown", "label": "不确定，暂时跳过"}
                ]
            }
            questions.append(question)
        
        return questions
    
    def format_confirmation_dialog(self, config: CostLinkConfig) -> str:
        """
        格式化确认对话框内容
        
        Args:
            config: 成本环节配置
        
        Returns:
            格式化后的确认内容
        """
        lines = [
            "\n" + "="*60,
            "【成本环节确认】",
            "="*60,
            "\n根据您提供的业务信息，系统识别到以下成本环节：\n"
        ]
        
        # 有明确数据的环节
        available_links = config.get_links_with_data()
        if available_links:
            lines.append("✅ 已识别到数据的环节（将参与计算）：")
            for link in available_links:
                lines.append(f"   • {link.name}: {link.description}")
            lines.append("")
        
        # 需要确认的环节
        uncertain_links = config.get_links_needing_confirmation()
        if uncertain_links:
            lines.append("❓ 需要您确认的环节：")
            for i, link in enumerate(uncertain_links, 1):
                lines.append(f"   {i}. {link.name}")
                lines.append(f"      说明: {link.description}")
            lines.append("")
            lines.append("请回复：")
            lines.append("  • '确认全部' - 启用所有环节")
            lines.append("  • '跳过XX,YY' - 跳过指定环节")
            lines.append("  • 'XX不需要' - 指定环节不参与")
            lines.append("")
        
        # 不适用的环节
        inactive_links = [l for l in config.get_all_links() if not l.is_active and not l.is_custom]
        if inactive_links:
            lines.append("❌ 根据业务类型默认不参与的环节：")
            for link in inactive_links:
                lines.append(f"   • {link.name}: {link.description}")
            lines.append("")
        
        # 自定义环节提示
        lines.append("💡 提示：")
        lines.append("   如果业务涉及其他未列出的成本环节，请描述该环节，")
        lines.append("   系统将分析是否可以作为自定义环节添加。")
        lines.append("="*60)
        
        return "\n".join(lines)


class CostLinkConfirmationHandler:
    """
    环节确认处理器
    
    处理用户对环节的确认回复
    """
    
    def __init__(self):
        """初始化处理器"""
        pass
    
    def parse_confirmation(self, user_response: str, config: CostLinkConfig) -> Dict[str, Any]:
        """
        解析用户的确认回复
        
        Args:
            user_response: 用户回复
            config: 当前配置
        
        Returns:
            解析结果
        """
        user_response = user_response.strip().lower()
        result = {
            "confirmed_active": [],
            "confirmed_inactive": [],
            "need_data_input": [],
            "custom_link_request": None,
            "action": None
        }
        
        # 确认全部
        if "确认全部" in user_response or "全部确认" in user_response or "全部" == user_response:
            result["action"] = "confirm_all"
            for link in config.get_links_needing_confirmation():
                result["confirmed_active"].append(link.name)
            return result
        
        # 跳过某些环节
        if "跳过" in user_response:
            result["action"] = "skip_some"
            # 提取跳过的环节名称
            for link in config.get_all_links():
                if link.name in user_response or link.name_en in user_response:
                    if "跳过" in user_response[user_response.find(link.name):user_response.find(link.name)+len(link.name)+10]:
                        result["confirmed_inactive"].append(link.name)
        
        # 指定环节不需要
        for link in config.get_all_links():
            if link.name in user_response:
                if "不需要" in user_response or "不涉及" in user_response or "没有" in user_response:
                    result["confirmed_inactive"].append(link.name)
                elif "需要" in user_response or "有" in user_response:
                    result["confirmed_active"].append(link.name)
        
        # 检查是否是自定义环节请求
        if any(kw in user_response for kw in ["额外", "还有", "另外", "其他", "自定义"]):
            result["custom_link_request"] = user_response
        
        return result
    
    def apply_confirmation(self, config: CostLinkConfig, confirmation: Dict[str, Any]) -> CostLinkConfig:
        """
        应用确认结果到配置
        
        Args:
            config: 原始配置
            confirmation: 确认结果
        
        Returns:
            更新后的配置
        """
        # 启用确认的环节
        for link_name in confirmation.get("confirmed_active", []):
            link = config.get_link_by_name(link_name)
            if link:
                link.is_active = True
                link.data_status = "available"
                link.user_confirmed = True
        
        # 禁用确认的环节
        for link_name in confirmation.get("confirmed_inactive", []):
            link = config.get_link_by_name(link_name)
            if link:
                link.is_active = False
                link.data_status = "not_applicable"
                link.user_confirmed = True
        
        return config
    
    def check_need_more_data(self, config: CostLinkConfig) -> Tuple[bool, List[str]]:
        """
        检查是否需要更多数据
        
        Args:
            config: 当前配置
        
        Returns:
            (是否需要, 需要数据的环节列表)
        """
        need_data_links = []
        
        for link in config.get_active_links():
            if link.data_status == "unknown":
                need_data_links.append(link.name)
        
        return len(need_data_links) > 0, need_data_links
