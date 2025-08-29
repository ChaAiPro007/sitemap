"""
Sitemap分类器
根据URL特征自动分类为game或tool
"""

import re
import yaml
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path
import logging

from ..utils import get_logger


class SitemapClassifier:
    """Sitemap分类器 - 自动识别游戏或工具类网站"""
    
    def __init__(self, config_path: str = None):
        """
        初始化分类器
        
        Args:
            config_path: 分类配置文件路径
        """
        self.logger = get_logger(__name__)
        
        # 默认配置路径
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'sitemap_categories.yaml'
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.compiled_patterns = self._compile_patterns()
        
        # 缓存分类结果
        self._cache = {} if self.config.get('options', {}).get('cache_results', True) else None
        
        self.logger.info(f"SitemapClassifier初始化完成，配置文件: {self.config_path}")
    
    def _load_config(self) -> Dict:
        """加载分类配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.logger.debug(f"成功加载分类配置: {self.config_path}")
                return config
        except Exception as e:
            self.logger.error(f"加载分类配置失败: {e}")
            # 返回默认配置
            return {
                'categories': {
                    'game': {'exact_domains': [], 'domain_patterns': [], 'path_patterns': [], 'keywords': []},
                    'tool': {'exact_domains': [], 'domain_patterns': [], 'path_patterns': [], 'keywords': []}
                },
                'default_category': 'tool',
                'options': {'case_sensitive': False, 'log_classification': True, 'cache_results': True}
            }
    
    def _compile_patterns(self) -> Dict[str, Dict[str, List]]:
        """预编译所有正则表达式模式"""
        compiled = {
            'domain': {'game': [], 'tool': []},
            'path': {'game': [], 'tool': []}
        }
        
        flags = 0 if self.config.get('options', {}).get('case_sensitive', False) else re.IGNORECASE
        
        for category, cat_config in self.config.get('categories', {}).items():
            # 编译域名模式
            for pattern in cat_config.get('domain_patterns', []):
                try:
                    compiled_pattern = re.compile(pattern, flags)
                    compiled['domain'][category].append(compiled_pattern)
                except re.error as e:
                    self.logger.error(f"编译域名模式失败 {category} - {pattern}: {e}")
            
            # 编译路径模式
            for pattern in cat_config.get('path_patterns', []):
                try:
                    compiled_pattern = re.compile(pattern, flags)
                    compiled['path'][category].append(compiled_pattern)
                except re.error as e:
                    self.logger.error(f"编译路径模式失败 {category} - {pattern}: {e}")
        
        return compiled
    
    def classify_url(self, url: str) -> Tuple[str, str]:
        """
        分类单个URL
        
        Args:
            url: 待分类的URL
        
        Returns:
            Tuple[str, str]: (分类结果, 分类原因)
                分类结果: "game" | "tool"
                分类原因: 例如 "exact_domain_match", "domain_pattern_match", etc.
        """
        # 检查缓存
        if self._cache is not None and url in self._cache:
            return self._cache[url]
        
        # 解析URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower() if not self.config.get('options', {}).get('case_sensitive', False) else parsed_url.netloc
        path = parsed_url.path
        
        # 移除www前缀进行匹配
        domain_without_www = domain.replace('www.', '', 1)
        
        # 1. 精确域名匹配（最高优先级）
        for category, cat_config in self.config.get('categories', {}).items():
            exact_domains = cat_config.get('exact_domains', [])
            if not self.config.get('options', {}).get('case_sensitive', False):
                exact_domains = [d.lower() for d in exact_domains]
            
            if domain in exact_domains or domain_without_www in exact_domains:
                result = (category, "exact_domain_match")
                if self.config.get('options', {}).get('log_classification', True):
                    self.logger.debug(f"URL分类: {url} -> {category} (精确域名匹配)")
                if self._cache is not None:
                    self._cache[url] = result
                return result
        
        # 2. 域名模式匹配
        for category, patterns in self.compiled_patterns['domain'].items():
            for pattern in patterns:
                if pattern.search(domain) or pattern.search(domain_without_www):
                    result = (category, f"domain_pattern_match:{pattern.pattern}")
                    if self.config.get('options', {}).get('log_classification', True):
                        self.logger.debug(f"URL分类: {url} -> {category} (域名模式匹配: {pattern.pattern})")
                    if self._cache is not None:
                        self._cache[url] = result
                    return result
        
        # 3. 路径模式匹配
        for category, patterns in self.compiled_patterns['path'].items():
            for pattern in patterns:
                if pattern.search(path):
                    result = (category, f"path_pattern_match:{pattern.pattern}")
                    if self.config.get('options', {}).get('log_classification', True):
                        self.logger.debug(f"URL分类: {url} -> {category} (路径模式匹配: {pattern.pattern})")
                    if self._cache is not None:
                        self._cache[url] = result
                    return result
        
        # 4. 默认分类
        default = self.config.get('default_category', 'tool')
        result = (default, "default_classification")
        if self.config.get('options', {}).get('log_classification', True):
            self.logger.debug(f"URL分类: {url} -> {default} (默认分类)")
        if self._cache is not None:
            self._cache[url] = result
        return result
    
    def classify_batch(self, urls: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """
        批量分类URLs
        
        Args:
            urls: URL列表
        
        Returns:
            分类结果字典: {
                "game": {"urls": [...], "count": n, "reasons": {...}},
                "tool": {"urls": [...], "count": n, "reasons": {...}}
            }
        """
        result = {
            "game": {"urls": [], "count": 0, "reasons": {}},
            "tool": {"urls": [], "count": 0, "reasons": {}}
        }
        
        for url in urls:
            category, reason = self.classify_url(url)
            result[category]["urls"].append(url)
            result[category]["count"] += 1
            
            # 统计分类原因
            if reason not in result[category]["reasons"]:
                result[category]["reasons"][reason] = 0
            result[category]["reasons"][reason] += 1
        
        # 记录统计信息
        self.logger.info(f"批量分类完成: 总计{len(urls)}个URL")
        self.logger.info(f"  - 游戏类(game): {result['game']['count']}个")
        self.logger.info(f"  - 工具类(tool): {result['tool']['count']}个")
        
        return result
    
    def classify_url_keywords_map(self, url_keywords_map: Dict[str, any]) -> Dict[str, Dict[str, any]]:
        """
        分类URL-关键词映射
        
        Args:
            url_keywords_map: URL到关键词的映射
        
        Returns:
            按分类分组的映射: {"game": {url: keywords}, "tool": {url: keywords}}
        """
        classified = {
            "game": {},
            "tool": {}
        }
        
        for url, keywords in url_keywords_map.items():
            category, _ = self.classify_url(url)
            classified[category][url] = keywords
        
        self.logger.info(f"URL-关键词映射分类完成:")
        self.logger.info(f"  - 游戏类(game): {len(classified['game'])}个")
        self.logger.info(f"  - 工具类(tool): {len(classified['tool'])}个")
        
        return classified
    
    def get_statistics(self) -> Dict:
        """获取分类统计信息"""
        stats = {
            'total_classified': len(self._cache) if self._cache else 0,
            'cache_size': len(self._cache) if self._cache else 0,
            'config_loaded': self.config is not None,
            'categories': list(self.config.get('categories', {}).keys()),
            'default_category': self.config.get('default_category', 'tool')
        }
        
        if self._cache:
            # 统计缓存中的分类分布
            category_counts = {}
            reason_counts = {}
            for (category, reason) in self._cache.values():
                category_counts[category] = category_counts.get(category, 0) + 1
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            stats['category_distribution'] = category_counts
            stats['reason_distribution'] = reason_counts
        
        return stats
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache is not None:
            self._cache.clear()
            self.logger.info("分类缓存已清空")
    
    def reload_config(self):
        """重新加载配置"""
        self.config = self._load_config()
        self.compiled_patterns = self._compile_patterns()
        self.clear_cache()
        self.logger.info("分类配置已重新加载")