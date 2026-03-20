"""
向量数据库模块 - 修复版本

使用ChromaDB存储和检索向量化文档
兼容新旧版本ChromaDB
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import chromadb


class VectorStore:
    """
    向量存储
    
    基于ChromaDB的向量数据库，支持文档的存储和语义检索
    兼容ChromaDB新旧版本
    """
    
    def __init__(self, collection_name: str = "logistics_knowledge", persist_dir: str = None):
        """
        初始化向量存储
        
        Args:
            collection_name: 集合名称
            persist_dir: 持久化目录
        """
        if persist_dir is None:
            persist_dir = Path(__file__).parent.parent.parent / "data" / "chroma_db"
        
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化ChromaDB客户端（兼容新旧版本）
        self.client = None
        self.collection = None
        
        try:
            # 尝试新版本的方式 (ChromaDB 0.4.0+)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir)
            )
            print(f"使用新版ChromaDB客户端 (PersistentClient)")
        except Exception as e1:
            print(f"新版客户端初始化失败: {e1}")
            try:
                # 尝试旧版本方式
                from chromadb.config import Settings
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(self.persist_dir)
                ))
                print(f"使用旧版ChromaDB客户端 (Client with Settings)")
            except Exception as e2:
                print(f"旧版客户端初始化也失败: {e2}")
                raise RuntimeError(f"无法初始化ChromaDB: {e1}, {e2}")
        
        # 获取或创建集合
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"向量存储初始化完成: {collection_name}")
            print(f"当前文档数: {self.collection.count()}")
        except Exception as e:
            print(f"集合初始化失败: {e}")
            raise
    
    def add_documents(
        self, 
        documents: List[str], 
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None
    ) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: 文档ID列表（可选）
        
        Returns:
            文档ID列表
        """
        if not documents:
            return []
        
        # 生成ID
        if ids is None:
            ids = [hashlib.md5(doc.encode()).hexdigest() for doc in documents]
        
        # 添加文档
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # 持久化（兼容新旧版本）
        try:
            self.client.persist()
        except AttributeError:
            pass  # 新版本不需要手动调用
        
        return ids
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        filter_dict: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        语义检索
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            检索结果列表
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict
            )
            
            # 格式化结果
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0
                })
            
            return formatted_results
        except Exception as e:
            print(f"检索失败: {e}")
            return []
    
    def delete(self, ids: List[str]):
        """
        删除文档
        
        Args:
            ids: 文档ID列表
        """
        self.collection.delete(ids=ids)
        # 持久化（兼容新旧版本）
        try:
            self.client.persist()
        except AttributeError:
            pass
    
    def update(
        self, 
        ids: List[str],
        documents: List[str] = None,
        metadatas: List[Dict[str, Any]] = None
    ):
        """
        更新文档
        
        Args:
            ids: 文档ID列表
            documents: 新文档内容
            metadatas: 新元数据
        """
        if documents:
            self.collection.update(
                ids=ids,
                documents=documents
            )
        elif metadatas:
            self.collection.update(
                ids=ids,
                metadatas=metadatas
            )
        
        # 持久化（兼容新旧版本）
        try:
            self.client.persist()
        except AttributeError:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            return {
                "total_documents": self.collection.count(),
                "collection_name": self.collection.name,
                "persist_directory": str(self.persist_dir)
            }
        except:
            return {
                "total_documents": 0,
                "collection_name": "unknown",
                "persist_directory": str(self.persist_dir)
            }


if __name__ == "__main__":
    # 测试向量存储
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    print("="*60)
    print("向量存储测试")
    print("="*60)
    
    try:
        store = VectorStore()
        print("\n✅ 向量存储初始化成功")
        
        # 添加测试文档
        test_docs = [
            "物流成本包括运输成本、仓储成本、人工成本等",
            "TOB企业购业务通常涉及大批量配送",
            "餐配业务需要冷链运输以保证食品安全"
        ]
        
        ids = store.add_documents(test_docs)
        print(f"✅ 添加 {len(ids)} 个文档")
        
        # 测试检索
        results = store.search("物流成本", n_results=2)
        print(f"\n✅ 检索到 {len(results)} 个结果")
        for r in results:
            print(f"  - {r['content'][:50]}...")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
