"""
RAG引擎

检索增强生成：结合向量检索和LLM生成
"""

from typing import Dict, Any, List, Optional
from .vector_store import VectorStore
from .document_loader import DocumentLoader
from ..llm import SiliconFlowClient


class RAGEngine:
    """
    RAG引擎
    
    提供基于检索的问答能力
    """
    
    def __init__(self):
        """初始化RAG引擎"""
        self.vector_store = VectorStore()
        self.document_loader = DocumentLoader()
        self.llm_client = SiliconFlowClient()
        
        # 初始化时加载知识库
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """初始化知识库"""
        stats = self.vector_store.get_stats()
        
        if stats["total_documents"] == 0:
            print("向量库为空，正在加载知识库...")
            documents = self.document_loader.load_knowledge_base()
            
            if documents:
                self.add_documents(documents)
                print(f"已加载 {len(documents)} 个文档到向量库")
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        添加文档到RAG系统
        
        Args:
            documents: 文档列表，每个文档包含content和metadata
        """
        texts = [doc["content"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        
        self.vector_store.add_documents(texts, metadatas)
    
    def query(self, question: str, n_results: int = 3) -> Dict[str, Any]:
        """
        查询RAG系统
        
        Args:
            question: 问题
            n_results: 检索文档数量
        
        Returns:
            回答结果
        """
        # 1. 检索相关文档
        search_results = self.vector_store.search(question, n_results=n_results)
        
        if not search_results or not search_results['documents'][0]:
            return {
                "answer": "抱歉，我没有找到相关信息。",
                "sources": [],
                "confidence": 0.0
            }
        
        # 2. 构建上下文
        contexts = []
        sources = []
        
        for doc, metadata, distance in zip(
            search_results['documents'][0],
            search_results['metadatas'][0],
            search_results['distances'][0]
        ):
            contexts.append(doc)
            sources.append({
                "content": doc[:200] + "..." if len(doc) > 200 else doc,
                "metadata": metadata,
                "relevance": 1 - distance  # 转换为相似度
            })
        
        context_text = "\n\n".join([f"[文档{i+1}] {ctx}" for i, ctx in enumerate(contexts)])
        
        # 3. 构建Prompt
        prompt = f"""基于以下参考文档回答问题：

参考文档：
{context_text}

问题：{question}

要求：
1. 基于参考文档内容回答
2. 如果文档中没有相关信息，请明确说明
3. 回答要简洁、专业
4. 如有数据，请保留具体数字

请回答："""
        
        # 4. 调用LLM生成回答
        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是物流行业专家，基于提供的参考资料回答问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            answer = response["choices"][0]["message"]["content"]
            
            # 计算平均相关度
            avg_relevance = sum(s["relevance"] for s in sources) / len(sources)
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": avg_relevance,
                "context_used": context_text
            }
        
        except Exception as e:
            return {
                "answer": f"生成回答时出错: {str(e)}",
                "sources": sources,
                "confidence": 0.0
            }
    
    def query_with_filter(
        self, 
        question: str, 
        filter_dict: Dict[str, Any],
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        带过滤条件的查询
        
        Args:
            question: 问题
            filter_dict: 过滤条件
            n_results: 检索数量
        
        Returns:
            回答结果
        """
        # 检索
        search_results = self.vector_store.search(
            question, 
            n_results=n_results,
            filter_dict=filter_dict
        )
        
        if not search_results or not search_results['documents'][0]:
            return {
                "answer": "抱歉，在指定条件下没有找到相关信息。",
                "sources": [],
                "confidence": 0.0
            }
        
        # 构建上下文和生成回答（同上）
        contexts = search_results['documents'][0]
        context_text = "\n\n".join([f"[文档{i+1}] {ctx}" for i, ctx in enumerate(contexts)])
        
        prompt = f"""基于以下参考文档回答问题：

参考文档：
{context_text}

问题：{question}

请基于参考文档内容回答："""
        
        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是物流行业专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return {
                "answer": response["choices"][0]["message"]["content"],
                "sources": [
                    {
                        "content": doc[:200],
                        "metadata": meta
                    }
                    for doc, meta in zip(
                        search_results['documents'][0],
                        search_results['metadatas'][0]
                    )
                ],
                "confidence": 0.8
            }
        
        except Exception as e:
            return {
                "answer": f"生成回答时出错: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }
    
    def get_cost_insights_with_rag(
        self, 
        cost_structure: Dict[str, float],
        business_type: str
    ) -> Dict[str, Any]:
        """
        结合RAG获取成本洞察
        
        Args:
            cost_structure: 成本结构
            business_type: 业务类型
        
        Returns:
            洞察结果
        """
        # 找出高成本环节
        high_cost_items = sorted(
            cost_structure.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        insights = []
        
        for category, percentage in high_cost_items:
            # 查询相关知识
            query = f"{category}成本优化方法"
            result = self.query(query, n_results=2)
            
            insights.append({
                "category": category,
                "percentage": percentage,
                "insight": result["answer"],
                "sources": result["sources"]
            })
        
        return {
            "high_cost_categories": high_cost_items,
            "insights": insights
        }
    
    def add_file_to_knowledge_base(self, file_path: str) -> int:
        """
        添加文件到知识库
        
        Args:
            file_path: 文件路径
        
        Returns:
            添加的文档数
        """
        file_path = str(file_path)
        
        if file_path.endswith('.txt'):
            documents = self.document_loader.load_text_file(file_path)
        elif file_path.endswith('.md') or file_path.endswith('.markdown'):
            documents = self.document_loader.load_markdown(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            documents = self.document_loader.load_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path}")
        
        self.add_documents(documents)
        
        return len(documents)


if __name__ == "__main__":
    # 测试RAG引擎
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    print("="*60)
    print("RAG引擎测试")
    print("="*60)
    
    rag = RAGEngine()
    
    # 测试查询
    test_questions = [
        "TOB企业购业务有什么特点？",
        "如何降低配送成本？",
        "冷链运输需要注意什么？",
    ]
    
    for question in test_questions:
        print(f"\n问题: {question}")
        print("-"*60)
        
        result = rag.query(question)
        
        print(f"回答: {result['answer']}")
        print(f"置信度: {result['confidence']:.3f}")
        print(f"参考来源: {len(result['sources'])}个")
