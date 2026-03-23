"""
真正智能的统一对话界面

特点：
- LLM-native架构，LLM真正嵌入每个环节
- 支持文件上传（Excel等）
- 自然语言交互，无需固定流程
- 以"单"为基本计算单元，支持临时订单
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.llm_native_engine import LLMMissionEngineV2, TaskType, DataSource
from src.llm import SiliconFlowClient
from src.utils.file_processor import FileProcessor
from src.cost_engine.per_order_calculator import PerOrderCostCalculator
from src.models.order_unit import PerOrderParameters, OrderType


# 页面配置
st.set_page_config(
    page_title="物流业务智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def init_session_state():
    """初始化session state"""
    if 'engine' not in st.session_state:
        try:
            llm_client = SiliconFlowClient()
            st.session_state.engine = LLMMissionEngineV2(llm_client)
        except Exception as e:
            st.session_state.engine = LLMMissionEngineV2()

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'calculator' not in st.session_state:
        st.session_state.calculator = PerOrderCostCalculator()

    if 'file_processor' not in st.session_state:
        st.session_state.file_processor = FileProcessor()

    if 'current_data' not in st.session_state:
        st.session_state.current_data = {}


def add_message(role: str, content: str, message_type: str = "text"):
    """添加消息到历史"""
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "type": message_type
    })


def display_messages():
    """显示所有消息"""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["type"] == "table":
                st.markdown(msg["content"])
            elif msg["type"] == "success":
                st.success(msg["content"])
            elif msg["type"] == "error":
                st.error(msg["content"])
            elif msg["type"] == "warning":
                st.warning(msg["content"])
            else:
                st.markdown(msg["content"])


def process_file_upload(uploaded_file) -> dict:
    """处理文件上传"""
    if uploaded_file is None:
        return None
    
    try:
        file_content = uploaded_file.read()
        result = st.session_state.file_processor.process_file(
            file_content, 
            uploaded_file.name
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def perform_cost_calculation(context: dict) -> dict:
    """
    执行单均成本计算

    从上下文中提取数据，执行成本计算
    """
    data = context.get("collected_data", {})

    items = data.get("items_per_order")
    distance = data.get("distance_km")

    if not items or not distance:
        return {
            "success": False,
            "error": "缺少必要数据：每单件数和配送距离"
        }

    try:
        params = PerOrderParameters(
            order_type=OrderType(data.get("order_type", "single")),
            items_per_order=int(items),
            weight_per_item_kg=float(data.get("weight_per_item", 1.0)),
            distance_km=float(distance),
            floor=int(data.get("floor", 1)),
            has_elevator=data.get("has_elevator", True),
            need_upstairs=data.get("need_upstairs", False),
            need_cold_chain=data.get("need_cold_chain", False),
            purchase_price=data.get("purchase_price"),
            selling_price=data.get("selling_price"),
        )
        params.total_weight_kg = params.items_per_order * params.weight_per_item_kg

        result = st.session_state.calculator.calculate(params)
        result["params"] = params

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"计算失败: {str(e)}"
        }


def perform_profit_analysis(context: dict, cost_result: dict) -> dict:
    """
    执行利润分析

    结合成本和价格数据计算利润
    """
    data = context.get("collected_data", {})

    purchase_price = data.get("purchase_price")
    selling_price = data.get("selling_price")

    if purchase_price is None or selling_price is None:
        return None

    try:
        items = int(data.get("items_per_order", 1))
        logistics_cost = cost_result.get("total_cost", 0) if cost_result else 0

        product_cost_total = purchase_price * items
        revenue_total = selling_price * items

        total_cost = product_cost_total + logistics_cost
        profit = revenue_total - total_cost
        profit_margin = profit / revenue_total if revenue_total > 0 else 0

        if profit_margin < 0:
            feasibility = "not_recommended"
            feasibility_label = "❌ 不推荐"
        elif profit_margin < 0.1:
            feasibility = "caution"
            feasibility_label = "⚠️ 谨慎"
        elif profit_margin < 0.2:
            feasibility = "acceptable"
            feasibility_label = "✅ 可接受"
        else:
            feasibility = "recommended"
            feasibility_label = "✅✅ 强烈推荐"

        return {
            "product_cost": product_cost_total,
            "logistics_cost": logistics_cost,
            "total_cost": total_cost,
            "revenue": revenue_total,
            "profit": profit,
            "profit_margin": profit_margin,
            "feasibility": feasibility,
            "feasibility_label": feasibility_label,
            "break_even_price": round(logistics_cost / items, 2) if items > 0 else 0,
            "items": items,
        }

    except Exception as e:
        return None


def format_cost_result(result: dict) -> str:
    """格式化单均成本结果"""
    params = result.get("params")

    lines = [
        "\n## 📊 单均成本评估报告",
        "",
        f"**订单类型**: {result.get('order_type', '不确定')}",
        f"**每单件数**: {params.items_per_order if params else '?'}件",
        f"**总重量**: {params.total_weight_kg if params else '?'}kg",
        f"**配送距离**: {params.distance_km if params else '?'}km",
    ]

    if params and params.need_upstairs:
        lines.append(f"**上楼需求**: {params.floor}楼 (电梯: {'有' if params.has_elevator else '无'})")
    if params and params.need_cold_chain:
        lines.append("**冷链需求**: 需要")

    lines.extend(["", "### � 单均成本明细"])

    for item in result.get("cost_breakdown", []):
        lines.append(f"- {item['环节']}: ¥{item['成本']:.2f}")

    lines.extend([
        "",
        f"**单均总成本**: ¥{result.get('total_cost', 0):.2f}",
        f"**单件成本**: ¥{result.get('cost_per_item', 0):.2f}",
    ])

    return "\n".join(lines)


def format_profit_result(result: dict) -> str:
    """格式化利润结果"""
    feasibility_labels = {
        "recommended": "✅ 推荐",
        "acceptable": "⚠️ 可接受",
        "caution": "⚠️ 谨慎",
        "not_recommended": "❌ 不推荐"
    }

    lines = [
        "\n## 💹 订单可行性分析",
        "",
        "### 📊 成本与收入",
        f"- 商品成本: ¥{result.get('product_cost', 0):.2f}",
        f"- 物流成本: ¥{result.get('logistics_cost', 0):.2f}",
        f"- 总成本: ¥{result.get('total_cost', 0):.2f}",
        f"- 销售收入: ¥{result.get('revenue', 0):.2f}",
        "",
        "### 💰 利润分析",
        f"- 毛利: ¥{result.get('profit', 0):.2f}",
        f"- 毛利率: {result.get('profit_margin', 0):.1%}",
        f"- 可行性: {result.get('feasibility_label', '未知')}",
        f"- 盈亏平衡售价: ¥{result.get('break_even_price', 0):.2f}/件",
    ]

    return "\n".join(lines)


def build_data_summary(data: dict) -> str:
    """构建数据摘要供用户确认"""
    lines = [
        "\n## 📋 信息确认",
        "",
        "已识别到以下信息：",
    ]

    items = data.get("items_per_order")
    weight = data.get("weight_per_item_kg")
    distance = data.get("distance_km")
    order_type = data.get("order_type", "不确定")
    purchase_price = data.get("purchase_price")
    selling_price = data.get("selling_price")
    need_upstairs = data.get("need_upstairs", False)
    need_cold_chain = data.get("need_cold_chain", False)
    floor = data.get("floor", 1)

    if items:
        lines.append(f"- **订单数量**: {items}件")
    if weight:
        lines.append(f"- **单件重量**: {weight}kg")
    if distance:
        lines.append(f"- **配送距离**: {distance}km")
    lines.append(f"- **订单类型**: {order_type}")

    if need_upstairs:
        lines.append(f"- **上楼需求**: 需要上{floor}楼")
    if need_cold_chain:
        lines.append(f"- **冷链需求**: 需要")

    if purchase_price and selling_price:
        lines.append(f"- **采购价**: ¥{purchase_price}")
        lines.append(f"- **售价**: ¥{selling_price}")

    lines.append("")
    lines.append("参与计算的环节：订单处理 → 拣选 → 包装 → 运输 → 末端配送")

    return "\n".join(lines)


def main():
    """主函数"""
    init_session_state()
    
    # 标题
    st.title("🤖 物流业务智能助手")
    st.markdown("---")
    
    # 欢迎消息
    if not st.session_state.messages:
        welcome = """
        👋 您好！我是您的物流业务智能助手。
        
        **我可以帮您：**
        - 📝 **评估物流成本** - 告诉我您的业务描述
        - 💹 **分析订单可行性** - 提供采购价和售价
        - 📊 **处理Excel数据** - 上传文件自动提取数据
        - ❓ **回答物流问题** - 关于成本、优化等
        
        **支持多种输入方式：**
        - 直接输入文字描述业务场景
        - 上传Excel文件（含订单、成本等数据）
        - 混合使用（文字 + 文件）
        
        请直接告诉我您的需求！
        """
        add_message("assistant", welcome)
    
    # 显示消息
    display_messages()
    
    # 文件上传区域
    st.markdown("---")
    with st.expander("📎 上传文件（Excel/CSV）", expanded=False):
        uploaded_file = st.file_uploader(
            "选择文件",
            type=["xlsx", "xls", "csv", "txt"],
            help="支持Excel、CSV和文本文件。系统会自动提取关键数据。"
        )
        
        if uploaded_file:
            with st.spinner("处理文件中..."):
                file_result = process_file_upload(uploaded_file)
            
            if file_result and file_result.get("success"):
                st.success(f"✅ 文件处理成功！")
                
                # 显示预览
                if file_result.get("data_type") == "excel":
                    st.markdown("**数据预览：**")
                    st.markdown(file_result.get("preview", ""))
                    
                    # 提取关键信息
                    key_info = file_result.get("key_info", {})
                    if key_info.get("detected_fields"):
                        st.markdown("**识别到的字段：**")
                        for field, info in key_info["detected_fields"].items():
                            st.write(f"  - {field}: 列「{info['column']}」")
                
                # 提取LLM友好的描述
                llm_text = st.session_state.file_processor.extract_for_llm(file_result)
                
                # 添加到对话
                add_message("user", f"上传了文件: {uploaded_file.name}\n\n请分析这个文件的数据。")
                
                # 调用LLM处理
                response = st.session_state.engine.process(llm_text)
                
                if response.get("success"):
                    # LLM理解了文件内容，提取了数据
                    # 将数据保存到上下文
                    extracted = response.get("extracted_data", {})
                    context = response.get("context", {})
                    
                    # 更新当前数据
                    collected = context.get("collected_data", {})
                    st.session_state.current_data.update(collected)
                    
                    # 如果有成本相关数据，询问是否计算
                    if context.get("current_task") in ["cost_assessment"]:
                        add_message("assistant", response.get("message"))
                    else:
                        add_message("assistant", response.get("message"))
                else:
                    add_message("error", f"处理文件失败: {file_result.get('error')}")
            else:
                st.error(f"处理文件失败: {file_result.get('error', '未知错误')}")
    
    # 用户输入
    user_input = st.chat_input("请输入您的需求...")
    
    if user_input:
        # 添加用户消息
        add_message("user", user_input)
        
        # 调用LLM引擎处理
        with st.spinner("🤔 思考中..."):
            response = st.session_state.engine.process(user_input)

        intent = response.get("intent")
        next_action = response.get("next_action")
        context = response.get("context", {})
        data = context.get("collected_data", {})

        has_minimal_data = data.get("items_per_order") and data.get("distance_km")

        if "pending_confirmation" not in st.session_state:
            st.session_state.pending_confirmation = False
        if "confirmed_data" not in st.session_state:
            st.session_state.confirmed_data = None

        should_calculate = False

        if st.session_state.pending_confirmation and user_input in ["确认", "是", "好的", "确认计算", "y", "yes"]:
            st.session_state.pending_confirmation = False
            st.session_state.confirmed_data = data
            should_calculate = True
        elif st.session_state.pending_confirmation:
            st.session_state.pending_confirmation = False
            add_message("assistant", "已取消计算，如有需要请重新描述。")
            st.rerun()
        elif has_minimal_data and next_action != "ask":
            summary = build_data_summary(data)
            add_message("assistant", summary + "\n\n请确认以上信息是否正确？回复「确认」开始计算，或补充其他信息。")
            st.session_state.pending_confirmation = True
            st.session_state.confirmed_data = data
            st.rerun()
        else:
            add_message("assistant", response.get("message"))

        if should_calculate and st.session_state.confirmed_data:
            data = st.session_state.confirmed_data
            confirmed_context = {"collected_data": data}
            calc_result = perform_cost_calculation(confirmed_context)

            if calc_result.get("success"):
                cost_result = calc_result.get("result")

                result_text = format_cost_result(cost_result)
                add_message("assistant", result_text, "table")

                if data.get("purchase_price") and data.get("selling_price"):
                    profit_result = perform_profit_analysis(confirmed_context, cost_result)
                    if profit_result:
                        profit_text = format_profit_result(profit_result)
                        add_message("assistant", profit_text, "table")

                personalized = response.get("personalized_advice", [])
                if personalized and isinstance(personalized, list):
                    advice_lines = ["\n\n## 💡 个性化建议"]
                    valid_count = 0
                    for advice in personalized:
                        if isinstance(advice, dict) and 'action' in advice:
                            valid_count += 1
                            action = advice.get('action', '优化建议')
                            savings = advice.get('savings', '待评估')
                            difficulty = advice.get('difficulty', '未知')
                            advice_lines.append(f"\n\n**{valid_count}. {action}")
                            advice_lines.append(f"\n   - 预期效果: {savings}")
                            advice_lines.append(f"\n   - 实施难度: {difficulty}")
                    if valid_count > 0:
                        add_message("assistant", "".join(advice_lines))

                add_message("assistant",
                    "\n\n💡 **提示**：您可以继续询问其他问题，或上传文件获取更多数据。")
            else:
                add_message("error", f"计算失败: {calc_result.get('error')}")
                # 添加LLM的回复
                add_message("assistant", response.get("message"))
        else:
            # 只是对话，还没有足够数据进行计算
            add_message("assistant", response.get("message"))
        
        # 重新显示消息
        st.rerun()
    
    # 侧边栏 - 功能说明
    with st.sidebar:
        st.markdown("### 🤖 功能说明")
        st.info("""
        **输入示例：**
        
        1. 成本评估
        "每天100单，要送到20公里外，每单5公斤"
        
        2. 利润分析
        "这单采购价50卖80，能做吗？"
        
        3. 文件+文字
        上传Excel后说"帮我分析这个"
        
        4. 模糊需求
        "我有个配送的活儿，帮我算算成本"
        """)
        
        st.markdown("---")
        
        if st.button("🗑️ 清空对话"):
            st.session_state.messages = []
            st.session_state.engine.reset()
            st.session_state.current_data = {}
            st.rerun()


if __name__ == "__main__":
    main()
