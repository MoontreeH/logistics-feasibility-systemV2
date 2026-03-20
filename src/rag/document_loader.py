"""
文档加载器

加载和解析各种格式的文档
"""

import re
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


class DocumentLoader:
    """
    文档加载器
    
    支持加载文本、Markdown、Excel等格式的文档
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化文档加载器
        
        Args:
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def load_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载文本文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            文档块列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分块
        chunks = self._split_text(content)
        
        return [
            {
                "content": chunk,
                "metadata": {
                    "source": file_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            for i, chunk in enumerate(chunks)
        ]
    
    def load_markdown(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载Markdown文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            文档块列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按标题分割
        sections = self._split_by_headers(content)
        
        documents = []
        for section in sections:
            chunks = self._split_text(section["content"])
            for i, chunk in enumerate(chunks):
                documents.append({
                    "content": chunk,
                    "metadata": {
                        "source": file_path,
                        "title": section["title"],
                        "level": section["level"],
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                })
        
        return documents
    
    def load_excel(self, file_path: str, sheet_name: int = 0) -> List[Dict[str, Any]]:
        """
        加载Excel文件
        
        Args:
            file_path: 文件路径
            sheet_name: 工作表名称或索引
        
        Returns:
            文档块列表
        """
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        documents = []
        
        # 将每行转换为文本
        for idx, row in df.iterrows():
            # 构建文本描述
            text_parts = []
            for col in df.columns:
                value = row[col]
                if pd.notna(value):
                    text_parts.append(f"{col}: {value}")
            
            content = "; ".join(text_parts)
            
            documents.append({
                "content": content,
                "metadata": {
                    "source": file_path,
                    "row_index": idx,
                    "type": "excel_row"
                }
            })
        
        return documents
    
    def load_directory(self, dir_path: str, extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        加载目录中的所有文档
        
        Args:
            dir_path: 目录路径
            extensions: 文件扩展名列表
        
        Returns:
            文档块列表
        """
        if extensions is None:
            extensions = ['.txt', '.md', '.markdown']
        
        dir_path = Path(dir_path)
        all_documents = []
        
        for ext in extensions:
            for file_path in dir_path.rglob(f"*{ext}"):
                if ext in ['.txt']:
                    docs = self.load_text_file(str(file_path))
                elif ext in ['.md', '.markdown']:
                    docs = self.load_markdown(str(file_path))
                else:
                    continue
                
                all_documents.extend(docs)
        
        return all_documents
    
    def load_knowledge_base(self) -> List[Dict[str, Any]]:
        """
        加载系统知识库
        
        Returns:
            文档列表
        """
        from ..knowledge import KnowledgeBase
        
        kb = KnowledgeBase()
        documents = []
        
        for item in kb.knowledge.values():
            content = f"{item.title}\n{item.content}"
            documents.append({
                "content": content,
                "metadata": {
                    "source": "knowledge_base",
                    "category": item.category,
                    "business_type": item.business_type,
                    "tags": item.tags,
                    "item_id": item.id
                }
            })
        
        return documents
    
    def _split_text(self, text: str) -> List[str]:
        """
        将文本分割成块
        
        Args:
            text: 原始文本
        
        Returns:
            文本块列表
        """
        # 按句子分割
        sentences = re.split(r'(?<=[。！？.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # 保存当前块
                chunks.append(''.join(current_chunk))
                
                # 保留重叠部分
                overlap_text = ''.join(current_chunk)[-self.chunk_overlap:]
                current_chunk = [overlap_text, sentence]
                current_length = len(overlap_text) + sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return chunks
    
    def _split_by_headers(self, text: str) -> List[Dict[str, Any]]:
        """
        按Markdown标题分割文本
        
        Args:
            text: Markdown文本
        
        Returns:
            分割后的段落列表
        """
        # 匹配Markdown标题
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        sections = []
        current_section = {"title": "", "level": 0, "content": ""}
        
        for line in text.split('\n'):
            match = re.match(header_pattern, line)
            if match:
                # 保存上一个段落
                if current_section["content"]:
                    sections.append(current_section)
                
                # 开始新段落
                level = len(match.group(1))
                title = match.group(2)
                current_section = {
                    "title": title,
                    "level": level,
                    "content": ""
                }
            else:
                current_section["content"] += line + "\n"
        
        # 添加最后一个段落
        if current_section["content"]:
            sections.append(current_section)
        
        return sections


if __name__ == "__main__":
    # 测试文档加载器
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    loader = DocumentLoader()
    
    print("="*60)
    print("文档加载器测试")
    print("="*60)
    
    # 测试知识库加载
    print("\n加载知识库...")
    docs = loader.load_knowledge_base()
    print(f"已加载 {len(docs)} 个文档")
    
    for doc in docs[:3]:
        print(f"\n文档: {doc['content'][:100]}...")
        print(f"元数据: {doc['metadata']}")
