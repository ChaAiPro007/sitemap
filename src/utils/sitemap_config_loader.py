"""
Sitemap配置加载器
从配置文件加载带类型的sitemap列表
"""

from typing import Dict, List, Tuple
from pathlib import Path
import logging

from ..utils import get_logger


class SitemapConfigLoader:
    """Sitemap配置加载器 - 读取带类型的sitemap配置"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = get_logger(__name__)
        
        # 默认配置文件路径
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'sitemaps_with_type.txt'
        
        self.config_path = Path(config_path)
        self.logger.info(f"配置加载器初始化，配置文件: {self.config_path}")
    
    def load_sitemaps(self) -> Dict[str, List[str]]:
        """
        加载sitemap配置
        
        Returns:
            按类型分组的sitemap字典: {"tool": [...], "game": [...]}
        """
        result = {
            "tool": [],
            "game": []
        }
        
        if not self.config_path.exists():
            self.logger.error(f"配置文件不存在: {self.config_path}")
            return result
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                line_number = 0
                for line in f:
                    line_number += 1
                    line = line.strip()
                    
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析格式: 类型|URL
                    if '|' not in line:
                        self.logger.warning(f"第{line_number}行格式错误，跳过: {line}")
                        continue
                    
                    parts = line.split('|', 1)
                    if len(parts) != 2:
                        self.logger.warning(f"第{line_number}行格式错误，跳过: {line}")
                        continue
                    
                    map_type = parts[0].strip().lower()
                    url = parts[1].strip()
                    
                    # 验证类型
                    if map_type not in ['tool', 'game']:
                        self.logger.warning(f"第{line_number}行类型无效({map_type})，跳过: {line}")
                        continue
                    
                    # 验证URL
                    if not url.startswith(('http://', 'https://')):
                        self.logger.warning(f"第{line_number}行URL无效，跳过: {url}")
                        continue
                    
                    # 添加到结果
                    result[map_type].append(url)
                    self.logger.debug(f"加载sitemap: {map_type} | {url}")
            
            # 统计信息
            self.logger.info(f"成功加载sitemap配置:")
            self.logger.info(f"  - 工具类(tool): {len(result['tool'])}个")
            self.logger.info(f"  - 游戏类(game): {len(result['game'])}个")
            
            return result
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return result
    
    def load_all_sitemaps(self) -> List[Tuple[str, str]]:
        """
        加载所有sitemap（带类型标记）
        
        Returns:
            列表，每个元素为(map_type, url)元组
        """
        grouped = self.load_sitemaps()
        result = []
        
        # 添加工具类
        for url in grouped['tool']:
            result.append(('tool', url))
        
        # 添加游戏类
        for url in grouped['game']:
            result.append(('game', url))
        
        return result
    
    def get_sitemaps_by_type(self, map_type: str) -> List[str]:
        """
        获取指定类型的sitemap列表
        
        Args:
            map_type: 类型 ("tool" 或 "game")
        
        Returns:
            URL列表
        """
        grouped = self.load_sitemaps()
        return grouped.get(map_type, [])