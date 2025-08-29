#!/usr/bin/env python3
"""
网站地图关键词分析工具 - 主程序入口
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime

from src.sitemap_analyzer import SitemapKeywordAnalyzer
from src.utils import setup_logging, get_logger, ensure_encryption_key, create_env_file_template
from src.utils import ensure_env_loaded, EnhancedEnvLoader


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description='网站地图关键词分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --config config/config.yaml --rules config/game_url_rules.yaml
  python main.py --sitemaps config/sitemaps.txt --log-level DEBUG
  python main.py --health-check
  python main.py --create-env
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/config.yaml',
        help='系统配置文件路径 (默认: config/config.yaml)'
    )
    
    parser.add_argument(
        '--rules', 
        default='config/game_url_rules.yaml',
        help='URL规则配置文件路径 (默认: config/game_url_rules.yaml)'
    )
    
    parser.add_argument(
        '--sitemaps', 
        help='Sitemap列表文件路径 (默认: config/sitemaps.txt)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别 (默认: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='日志文件路径 (默认: logs/sitemap_analyzer.log)'
    )
    
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='执行健康检查'
    )
    
    parser.add_argument(
        '--create-env',
        action='store_true',
        help='创建环境变量文件模板'
    )
    
    parser.add_argument(
        '--check-env',
        action='store_true',
        help='检查环境变量配置状态'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式，不实际提交数据'
    )
    
    
    return parser.parse_args()


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


def load_sitemap_urls(sitemaps_file: str = None) -> List[str]:
    """
    从环境变量或文件加载sitemap URL列表（兼容旧方式）
    Args:
        sitemaps_file: sitemap列表文件路径（可选，优先使用环境变量）

    Returns:
        List[str]: sitemap URL列表
    """
    # 优先从环境变量读取
    sitemap_urls_env = os.getenv('SITEMAP_URLS', '')
    if sitemap_urls_env:
        urls = [url.strip() for url in sitemap_urls_env.split(',') if url.strip()]
        print(f"从环境变量 SITEMAP_URLS 加载了 {len(urls)} 个sitemap URL")
        return urls

    # 如果环境变量没有配置，尝试从文件读取
    if sitemaps_file:
        sitemap_urls = []
        try:
            with open(sitemaps_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        sitemap_urls.append(line)
            print(f"从文件 {sitemaps_file} 加载了 {len(sitemap_urls)} 个sitemap URL")
            return sitemap_urls
        except FileNotFoundError:
            print(f"警告: sitemap文件不存在: {sitemaps_file}")
        except Exception as e:
            print(f"错误: 读取sitemap文件失败: {e}")

    # 如果都没有配置，返回空列表并提示
    print("错误: 未配置sitemap URL列表")
    print("请设置 SITEMAP_URLS 环境变量或提供 --sitemaps 文件路径")
    sys.exit(1)


def validate_config_files(config_path: str, rules_path: str) -> bool:
    """
    验证配置文件是否存在
    
    Args:
        config_path: 配置文件路径
        rules_path: 规则文件路径
        
    Returns:
        bool: 配置文件是否有效
    """
    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        return False
    
    if not Path(rules_path).exists():
        print(f"错误: 规则文件不存在: {rules_path}")
        return False
    
    return True


async def run_categorized_analysis(analyzer: SitemapKeywordAnalyzer, categorized_sitemaps: Dict[str, List[str]]) -> None:
    """
    运行分类的sitemap分析
    
    Args:
        analyzer: sitemap分析器实例
        categorized_sitemaps: 分类的sitemap字典 {"tool": [...], "game": [...]}
    """
    logger = get_logger(__name__)
    
    print("=" * 80)
    print("📊 Sitemap分类处理系统")
    print("=" * 80)
    print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
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
    
    # 导入所需模块
    from src.parsers.sitemap_parser import SitemapParser
    from src.extractors.keyword_extractor import KeywordExtractor
    from src.extractors.rule_engine import RuleEngine
    from src.api.simplified_backend_client import SimplifiedBackendClient
    from src.config.config import ConfigLoader
    
    # 初始化组件
    print("\n2️⃣ 初始化处理组件...")
    
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
    
    rule_engine = RuleEngine(rules)
    keyword_extractor = KeywordExtractor()
    backend_client = SimplifiedBackendClient()
    
    # 创建HTTP会话
    import aiohttp
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=10)
    session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    
    parser = SitemapParser(session=session, max_depth=2)
    
    try:
        all_tool_mappings = {}
        all_game_mappings = {}
        
        # 处理工具类sitemap
        if categorized_sitemaps['tool']:
            print("\n" + "=" * 80)
            print("3️⃣ 处理工具类(tool) sitemap")
            print("=" * 80)
            
            for idx, sitemap_url in enumerate(categorized_sitemaps['tool'], 1):
                print(f"\n[{idx}/{len(categorized_sitemaps['tool'])}] 处理: {sitemap_url}")
                print("-" * 60)
                
                try:
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"  ✅ 找到 {len(urls)} 个URL")
                    
                    url_keywords = {}
                    url_list = list(urls)[:100] if isinstance(urls, set) else urls[:100]
                    for url in url_list:
                        rule = rule_engine.get_rule_for_url(url)
                        keywords = keyword_extractor.extract_keywords(url, rule)
                        if keywords:
                            url_keywords[url] = keywords
                    
                    print(f"  ✅ 成功提取 {len(url_keywords)} 个关键词")
                    all_tool_mappings.update(url_keywords)
                    
                except Exception as e:
                    print(f"  ❌ 处理失败: {str(e)[:100]}")
        
        # 处理游戏类sitemap
        if categorized_sitemaps['game']:
            print("\n" + "=" * 80)
            print("4️⃣ 处理游戏类(game) sitemap") 
            print("=" * 80)
            
            for idx, sitemap_url in enumerate(categorized_sitemaps['game'], 1):
                print(f"\n[{idx}/{len(categorized_sitemaps['game'])}] 处理: {sitemap_url}")
                print("-" * 60)
                
                try:
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"  ✅ 找到 {len(urls)} 个URL")
                    
                    url_keywords = {}
                    url_list = list(urls)[:100] if isinstance(urls, set) else urls[:100]
                    for url in url_list:
                        rule = rule_engine.get_rule_for_url(url)
                        keywords = keyword_extractor.extract_keywords(url, rule)
                        if keywords:
                            url_keywords[url] = keywords
                    
                    print(f"  ✅ 成功提取 {len(url_keywords)} 个关键词")
                    all_game_mappings.update(url_keywords)
                    
                except Exception as e:
                    print(f"  ❌ 处理失败: {str(e)[:100]}")
        
        # 提交到API
        print("\n" + "=" * 80)
        print("5️⃣ 提交数据到API（带类型标识）")
        print("=" * 80)
        
        # 提交工具类数据
        if all_tool_mappings:
            print(f"\n🔧 提交工具类(tool)数据: {len(all_tool_mappings)}个URL")
            try:
                result = await backend_client.submit_url_keywords_mapping(
                    url_keywords_map=all_tool_mappings, 
                    map_type="tool"
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
                result = await backend_client.submit_url_keywords_mapping(
                    url_keywords_map=all_game_mappings, 
                    map_type="game"
                )
                if result:
                    print("  ✅ 游戏类数据提交成功 (mapType=game)")
                else:
                    print("  ❌ 游戏类数据提交失败")
            except Exception as e:
                print(f"  ❌ 提交异常: {e}")
        
        # 统计结果
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


async def run_health_check(analyzer: SitemapKeywordAnalyzer) -> None:
    """
    执行健康检查
    
    Args:
        analyzer: 分析器实例
    """
    logger = get_logger(__name__)
    
    print("执行健康检查...")
    health_status = await analyzer.health_check()
    
    print("\n健康检查结果:")
    print("-" * 40)
    
    all_healthy = True
    for component, status in health_status.items():
        status_text = "✓ 正常" if status else "✗ 异常"
        print(f"{component:15}: {status_text}")
        if not status:
            all_healthy = False
    
    print("-" * 40)
    
    if all_healthy:
        print("✓ 所有组件状态正常")
        logger.info("健康检查通过")
    else:
        print("✗ 部分组件状态异常")
        logger.warning("健康检查发现问题")
        sys.exit(1)


async def run_analysis(analyzer: SitemapKeywordAnalyzer, 
                      sitemap_urls: List[str]) -> None:
    """
    执行分析任务
    
    Args:
        analyzer: 分析器实例
        sitemap_urls: sitemap URL列表
    """
    logger = get_logger(__name__)
    
    if not sitemap_urls:
        logger.error("没有提供sitemap URL")
        sys.exit(1)
    
    logger.info(f"开始处理 {len(sitemap_urls)} 个sitemap")
    
    try:
        result = await analyzer.process_sitemaps(sitemap_urls)
        
        # 输出结果摘要
        print("\n处理结果摘要:")
        print("-" * 50)
        print(f"发现URL总数:     {result['total_urls_found']}")
        print(f"新URL数量:       {result['new_urls_processed']}")
        print(f"保存URL数量:     {result['urls_saved']}")
        print(f"提交记录数量:    {result['records_submitted']}")
        print("-" * 50)
        
        logger.info("分析任务完成")
        
    except Exception as e:
        logger.error(f"分析任务失败: {e}")
        sys.exit(1)


async def main() -> None:
    """主函数"""
    # 加载环境变量
    env_loader = ensure_env_loaded()
    
    if not env_loader.env_loaded:
        print("⚠️  环境变量加载警告 - 将使用系统环境变量")

    args = parse_arguments()

    # 创建环境变量文件
    if args.create_env:
        create_env_file_template()
        print("环境变量文件模板已创建: .env")
        return
    
    # 检查环境变量状态
    if args.check_env:
        print("🔍 环境变量配置状态")
        print("=" * 60)
        
        # 获取状态信息
        status = env_loader.get_status()
        validation = env_loader.validate_environment()
        
        # 基本信息
        print("\n📋 基本信息:")
        print(f"  环境文件: {'✅ 已加载' if status['loaded'] else '❌ 未加载'}")
        if status['env_file']:
            print(f"  文件路径: {status['env_file']}")
        print(f"  CI环境: {'✅ 是' if status['is_ci'] else '❌ 否'}")
        print(f"  GitHub Actions: {'✅ 是' if status['is_github_actions'] else '❌ 否'}")
        
        # 环境变量状态
        print("\n📊 环境变量状态:")
        for var_name, var_info in validation['variables'].items():
            if var_info['status'] == 'set':
                print(f"  ✅ {var_name}: 已设置 ({var_info['length']} 字符)")
            else:
                print(f"  ❌ {var_name}: {var_info['description']}")
        
        # 警告信息
        if validation['warnings']:
            print("\n⚠️  警告:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        # 验证结果
        if not validation['valid']:
            print("\n❌ 环境变量配置错误:")
            for error in validation['errors']:
                print(f"  - {error}")
            print("\n💡 解决方案:")
            print("  1. 设置所有必需的环境变量")
            print("  2. 确保URL以 http:// 或 https:// 开头")
            print("  3. 确保加密密钥至少32字符（推荐66字符）")
            print("  4. 运行 python main.py --create-env 创建模板文件")
            sys.exit(1)
        else:
            print("\n✅ 所有环境变量配置正确")
        
        return
    
    # 验证环境变量
    validation = env_loader.validate_environment()
    if not validation['valid']:
        print("❌ 环境变量验证失败:")
        for error in validation['errors']:
            print(f"   - {error}")
        print("\n💡 请检查并设置所有必需的环境变量")
        return
    
    # 确保加密密钥存在
    try:
        ensure_encryption_key()
    except ValueError as e:
        print(f"❌ 加密密钥错误: {e}")
        print("💡 请设置环境变量 ENCRYPTION_KEY，例如：")
        print("   export ENCRYPTION_KEY=your_encryption_key_here")
        return
    
    # 设置日志
    log_file = args.log_file or 'logs/sitemap_analyzer.log'
    setup_logging(
        config_file='config/logging.conf',
        log_level=args.log_level,
        log_file=log_file
    )
    
    logger = get_logger(__name__)
    logger.info("程序启动")
    
    # 验证配置文件
    if not validate_config_files(args.config, args.rules):
        sys.exit(1)
    
    try:
        # 创建分析器
        analyzer = SitemapKeywordAnalyzer(args.config, args.rules)
        
        # 健康检查
        if args.health_check:
            await run_health_check(analyzer)
            return
        
        # 检查是否有分类配置
        categorized_sitemaps = load_categorized_sitemaps()
        
        if categorized_sitemaps['tool'] or categorized_sitemaps['game']:
            # 有分类配置，使用分类处理
            logger.info("检测到分类配置，使用分类模式处理")
            await run_categorized_analysis(analyzer, categorized_sitemaps)
        else:
            # 没有分类配置，使用旧方式处理
            logger.info("未检测到分类配置，使用传统模式处理")
            # 加载sitemap URL（优先从环境变量读取）
            sitemaps_file = args.sitemaps or 'config/sitemaps.txt'
            sitemap_urls = load_sitemap_urls(sitemaps_file)
            
            # 执行分析
            await run_analysis(analyzer, sitemap_urls)
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)
    finally:
        logger.info("程序结束")


if __name__ == '__main__':
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
