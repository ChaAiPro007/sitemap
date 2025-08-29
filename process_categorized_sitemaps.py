#!/usr/bin/env python3
"""
通过环境变量处理分类的sitemap
明确区分工具类(tool)和游戏类(game)网站
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from src.parsers.sitemap_parser import SitemapParser
from src.extractors.keyword_extractor import KeywordExtractor
from src.extractors.rule_engine import RuleEngine
from src.api.simplified_backend_client import SimplifiedBackendClient
from src.config.config import ConfigLoader


def load_categorized_sitemaps() -> Dict[str, List[str]]:
    """
    从环境变量加载分类的sitemap
    
    Returns:
        按类型分组的sitemap字典: {"tool": [...], "game": [...]}
    """
    result = {
        "tool": [],
        "game": []
    }
    
    # 加载工具类sitemap
    tool_sitemaps = os.getenv('TOOL_SITEMAPS', '')
    if tool_sitemaps:
        result['tool'] = [url.strip() for url in tool_sitemaps.split(',') if url.strip()]
        print(f"✅ 从TOOL_SITEMAPS加载了 {len(result['tool'])} 个工具类网站")
    
    # 加载游戏类sitemap
    game_sitemaps = os.getenv('GAME_SITEMAPS', '')
    if game_sitemaps:
        result['game'] = [url.strip() for url in game_sitemaps.split(',') if url.strip()]
        print(f"✅ 从GAME_SITEMAPS加载了 {len(result['game'])} 个游戏类网站")
    
    # 兼容旧配置：如果没有分类配置，尝试读取SITEMAP_URLS（默认为tool类型）
    if not result['tool'] and not result['game']:
        old_sitemaps = os.getenv('SITEMAP_URLS', '')
        if old_sitemaps:
            result['tool'] = [url.strip() for url in old_sitemaps.split(',') if url.strip()]
            print(f"⚠️ 使用旧配置SITEMAP_URLS，默认作为工具类处理: {len(result['tool'])} 个网站")
    
    return result


async def process_categorized_sitemaps():
    """按类型处理sitemap（从环境变量读取）"""
    
    print("=" * 80)
    print("📊 Sitemap分类处理系统（环境变量版）")
    print("=" * 80)
    print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 1. 从环境变量加载分类sitemap
    print("\n1️⃣ 从环境变量加载分类sitemap...")
    categorized_sitemaps = load_categorized_sitemaps()
    
    if not categorized_sitemaps['tool'] and not categorized_sitemaps['game']:
        print("❌ 没有配置任何sitemap！")
        print("请在.env文件中设置：")
        print("  - TOOL_SITEMAPS: 工具类网站sitemap")
        print("  - GAME_SITEMAPS: 游戏类网站sitemap")
        print("  - SITEMAP_URLS: 兼容旧配置（默认为tool类型）")
        return
    
    # 显示配置信息
    print(f"\n📋 配置的sitemap统计:")
    print(f"  🔧 工具类(tool): {len(categorized_sitemaps['tool'])}个")
    if categorized_sitemaps['tool']:
        for i, url in enumerate(categorized_sitemaps['tool'][:3], 1):
            print(f"     {i}. {url}")
        if len(categorized_sitemaps['tool']) > 3:
            print(f"     ... 还有{len(categorized_sitemaps['tool'])-3}个")
    
    print(f"\n  🎮 游戏类(game): {len(categorized_sitemaps['game'])}个")
    if categorized_sitemaps['game']:
        for i, url in enumerate(categorized_sitemaps['game'][:3], 1):
            print(f"     {i}. {url}")
        if len(categorized_sitemaps['game']) > 3:
            print(f"     ... 还有{len(categorized_sitemaps['game'])-3}个")
    
    # 2. 初始化组件
    print("\n2️⃣ 初始化处理组件...")
    
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
        if categorized_sitemaps['tool']:
            print("\n" + "=" * 80)
            print("3️⃣ 处理工具类(tool) sitemap")
            print("=" * 80)
            
            for idx, sitemap_url in enumerate(categorized_sitemaps['tool'], 1):
                print(f"\n[{idx}/{len(categorized_sitemaps['tool'])}] 处理: {sitemap_url}")
                print("-" * 60)
                
                try:
                    # 解析sitemap
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"  ✅ 找到 {len(urls)} 个URL")
                    
                    # 提取关键词
                    url_keywords = {}
                    # 转换为列表以支持切片
                    url_list = list(urls)[:100] if isinstance(urls, set) else urls[:100]
                    for url in url_list:  # 限制处理前100个
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
        if categorized_sitemaps['game']:
            print("\n" + "=" * 80)
            print("4️⃣ 处理游戏类(game) sitemap")
            print("=" * 80)
            
            for idx, sitemap_url in enumerate(categorized_sitemaps['game'], 1):
                print(f"\n[{idx}/{len(categorized_sitemaps['game'])}] 处理: {sitemap_url}")
                print("-" * 60)
                
                try:
                    # 解析sitemap
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"  ✅ 找到 {len(urls)} 个URL")
                    
                    # 提取关键词
                    url_keywords = {}
                    # 转换为列表以支持切片
                    url_list = list(urls)[:100] if isinstance(urls, set) else urls[:100]
                    for url in url_list:  # 限制处理前100个
                        rule = rule_engine.get_rule_for_url(url)
                        keywords = keyword_extractor.extract_keywords(url, rule)
                        if keywords:
                            url_keywords[url] = keywords
                    
                    print(f"  ✅ 成功提取 {len(url_keywords)} 个关键词")
                    
                    # 合并到总映射
                    all_game_mappings.update(url_keywords)
                    
                except Exception as e:
                    print(f"  ❌ 处理失败: {str(e)[:100]}")
        
        # 6. 提交到API（明确标注类型）
        print("\n" + "=" * 80)
        print("5️⃣ 提交数据到API（带类型标识）")
        print("=" * 80)
        
        # 提交工具类数据
        if all_tool_mappings:
            print(f"\n🔧 提交工具类(tool)数据: {len(all_tool_mappings)}个URL")
            try:
                # 明确指定mapType="tool"
                result = await backend_client.submit_url_keywords_mapping(
                    url_keywords_map=all_tool_mappings, 
                    map_type="tool"  # 明确标注为工具类
                )
                if result:
                    print("  ✅ 工具类数据提交成功 (mapType=tool)")
                else:
                    print("  ❌ 工具类数据提交失败")
            except Exception as e:
                print(f"  ❌ 提交异常: {e}")
        
        # 提交游戏类数据
        if all_game_mappings:
            print(f"\n🎮 提交游戏类(game)数据: {len(all_game_mappings)}个URL")
            try:
                # 明确指定mapType="game"
                result = await backend_client.submit_url_keywords_mapping(
                    url_keywords_map=all_game_mappings, 
                    map_type="game"  # 明确标注为游戏类
                )
                if result:
                    print("  ✅ 游戏类数据提交成功 (mapType=game)")
                else:
                    print("  ❌ 游戏类数据提交失败")
            except Exception as e:
                print(f"  ❌ 提交异常: {e}")
        
        # 7. 统计结果
        print("\n" + "=" * 80)
        print("6️⃣ 处理结果统计")
        print("=" * 80)
        print(f"🔧 工具类(tool):")
        print(f"  - 处理sitemap: {len(categorized_sitemaps['tool'])}个")
        print(f"  - 提取关键词: {len(all_tool_mappings)}个")
        print(f"  - 提交类型: mapType='tool'")
        
        print(f"\n🎮 游戏类(game):")
        print(f"  - 处理sitemap: {len(categorized_sitemaps['game'])}个")
        print(f"  - 提取关键词: {len(all_game_mappings)}个")
        print(f"  - 提交类型: mapType='game'")
        
        print(f"\n📊 总计:")
        print(f"  - 处理sitemap: {len(categorized_sitemaps['tool']) + len(categorized_sitemaps['game'])}个")
        print(f"  - 提取关键词: {len(all_tool_mappings) + len(all_game_mappings)}个")
        print(f"  - 分类提交: tool和game分别提交")
        
    finally:
        await session.close()
    
    print("\n" + "=" * 80)
    print(f"✅ 处理完成!")
    print(f"🕐 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(process_categorized_sitemaps())