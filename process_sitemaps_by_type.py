#!/usr/bin/env python3
"""
按类型处理sitemap
从配置文件读取带类型的sitemap列表并分别处理
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# 设置环境变量
os.environ['ENCRYPTION_KEY'] = 'anDXpvd1B1fFizhhgOJe9qLvOLvxkqyo6g0nYOIiQqw='
os.environ['SITEMAP_API_URL'] = 'http://localhost:5001/api/sitemap/keywords'
os.environ['SITEMAP_SECRET_KEY'] = 'test-key-2024'

from src.utils.sitemap_config_loader import SitemapConfigLoader
from src.parsers.sitemap_parser import SitemapParser
from src.extractors.keyword_extractor import KeywordExtractor
from src.extractors.rule_engine import RuleEngine
from src.api.simplified_backend_client import SimplifiedBackendClient
from src.config.config import ConfigLoader


async def process_sitemaps_by_type():
    """按类型处理sitemap"""
    
    print("=" * 80)
    print("Sitemap分类处理系统")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 1. 加载配置
    print("\n1. 加载sitemap配置...")
    config_loader = SitemapConfigLoader()
    sitemaps_by_type = config_loader.load_sitemaps()
    
    if not sitemaps_by_type['tool'] and not sitemaps_by_type['game']:
        print("❌ 没有配置任何sitemap")
        return
    
    # 显示配置信息
    print(f"\n配置的sitemap:")
    print(f"  🔧 工具类(tool): {len(sitemaps_by_type['tool'])}个")
    for i, url in enumerate(sitemaps_by_type['tool'][:3], 1):
        print(f"     {i}. {url}")
    if len(sitemaps_by_type['tool']) > 3:
        print(f"     ... 还有{len(sitemaps_by_type['tool'])-3}个")
    
    print(f"\n  🎮 游戏类(game): {len(sitemaps_by_type['game'])}个")
    for i, url in enumerate(sitemaps_by_type['game'][:3], 1):
        print(f"     {i}. {url}")
    if len(sitemaps_by_type['game']) > 3:
        print(f"     ... 还有{len(sitemaps_by_type['game'])-3}个")
    
    # 2. 初始化组件
    print("\n2. 初始化处理组件...")
    
    # 加载规则配置
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    rules_path = Path(__file__).parent / 'config' / 'url_rules.yaml'
    config_mgr = ConfigLoader(str(config_path), str(rules_path))
    
    try:
        config = config_mgr.load_system_config()
        print("  ✅ 系统配置加载成功")
    except:
        print("  ⚠️ 系统配置加载失败，使用默认配置")
        config = None
    
    rules = config_mgr.load_url_rules()
    print(f"  ✅ 加载了 {len(rules)} 个URL规则")
    
    # 初始化规则引擎和提取器
    rule_engine = RuleEngine(rules)
    keyword_extractor = KeywordExtractor()
    
    # 初始化API客户端
    backend_client = SimplifiedBackendClient()
    
    # 3. 创建HTTP会话
    import aiohttp
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=10)
    session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    
    # 初始化解析器
    parser = SitemapParser(session=session, max_depth=2)
    
    try:
        # 存储所有URL-关键词映射
        all_tool_mappings = {}
        all_game_mappings = {}
        
        # 4. 处理工具类sitemap
        if sitemaps_by_type['tool']:
            print("\n" + "=" * 80)
            print("3. 处理工具类(tool) sitemap")
            print("=" * 80)
            
            for idx, sitemap_url in enumerate(sitemaps_by_type['tool'], 1):
                print(f"\n[{idx}/{len(sitemaps_by_type['tool'])}] 处理: {sitemap_url}")
                print("-" * 60)
                
                try:
                    # 解析sitemap
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"  ✅ 找到 {len(urls)} 个URL")
                    
                    # 提取关键词
                    url_keywords = {}
                    for url in urls[:100]:  # 限制处理前100个
                        rule = rule_engine.get_rule_for_url(url)
                        keywords = keyword_extractor.extract_keywords(url, rule)
                        if keywords:
                            url_keywords[url] = keywords
                    
                    print(f"  ✅ 成功提取 {len(url_keywords)} 个关键词")
                    
                    # 合并到总映射
                    all_tool_mappings.update(url_keywords)
                    
                except Exception as e:
                    print(f"  ❌ 处理失败: {str(e)[:100]}")
        
        # 5. 处理游戏类sitemap
        if sitemaps_by_type['game']:
            print("\n" + "=" * 80)
            print("4. 处理游戏类(game) sitemap")
            print("=" * 80)
            
            for idx, sitemap_url in enumerate(sitemaps_by_type['game'], 1):
                print(f"\n[{idx}/{len(sitemaps_by_type['game'])}] 处理: {sitemap_url}")
                print("-" * 60)
                
                try:
                    # 解析sitemap
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"  ✅ 找到 {len(urls)} 个URL")
                    
                    # 提取关键词
                    url_keywords = {}
                    for url in urls[:100]:  # 限制处理前100个
                        rule = rule_engine.get_rule_for_url(url)
                        keywords = keyword_extractor.extract_keywords(url, rule)
                        if keywords:
                            url_keywords[url] = keywords
                    
                    print(f"  ✅ 成功提取 {len(url_keywords)} 个关键词")
                    
                    # 合并到总映射
                    all_game_mappings.update(url_keywords)
                    
                except Exception as e:
                    print(f"  ❌ 处理失败: {str(e)[:100]}")
        
        # 6. 提交到API
        print("\n" + "=" * 80)
        print("5. 提交数据到API")
        print("=" * 80)
        
        # 提交工具类数据
        if all_tool_mappings:
            print(f"\n提交工具类数据: {len(all_tool_mappings)}个URL")
            try:
                # 明确指定mapType="tool"，确保后端正确分类
                result = await backend_client.submit_url_keywords_mapping(
                    url_keywords_map=all_tool_mappings, 
                    map_type="tool"  # 明确指定为工具类
                )
                if result:
                    print("  ✅ 工具类数据提交成功")
                else:
                    print("  ❌ 工具类数据提交失败")
            except Exception as e:
                print(f"  ❌ 提交异常: {e}")
        
        # 提交游戏类数据
        if all_game_mappings:
            print(f"\n提交游戏类数据: {len(all_game_mappings)}个URL")
            try:
                # 明确指定mapType="game"，确保后端正确分类
                result = await backend_client.submit_url_keywords_mapping(
                    url_keywords_map=all_game_mappings, 
                    map_type="game"  # 明确指定为游戏类
                )
                if result:
                    print("  ✅ 游戏类数据提交成功")
                else:
                    print("  ❌ 游戏类数据提交失败")
            except Exception as e:
                print(f"  ❌ 提交异常: {e}")
        
        # 7. 统计结果
        print("\n" + "=" * 80)
        print("6. 处理结果统计")
        print("=" * 80)
        print(f"工具类(tool):")
        print(f"  - 处理sitemap: {len(sitemaps_by_type['tool'])}个")
        print(f"  - 提取关键词: {len(all_tool_mappings)}个")
        
        print(f"\n游戏类(game):")
        print(f"  - 处理sitemap: {len(sitemaps_by_type['game'])}个")
        print(f"  - 提取关键词: {len(all_game_mappings)}个")
        
        print(f"\n总计:")
        print(f"  - 处理sitemap: {len(sitemaps_by_type['tool']) + len(sitemaps_by_type['game'])}个")
        print(f"  - 提取关键词: {len(all_tool_mappings) + len(all_game_mappings)}个")
        
    finally:
        await session.close()
    
    print("\n" + "=" * 80)
    print(f"✅ 处理完成!")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(process_sitemaps_by_type())