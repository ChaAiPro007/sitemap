#!/usr/bin/env python3
"""
使用规则引擎的完整URL提取脚本
支持特殊域名规则
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import os

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置环境变量
os.environ['ENCRYPTION_KEY'] = 'anDXpvd1B1fFizhhgOJe9qLvOLvxkqyo6g0nYOIiQqw='
os.environ['SITEMAP_API_URL'] = 'http://localhost:5001/api/sitemap/keywords'
os.environ['SITEMAP_SECRET_KEY'] = 'test-key-2024'
os.environ['SITEMAP_URLS'] = 'https://example.com/sitemap.xml'

from src.parsers.sitemap_parser import SitemapParser
from src.extractors.rule_engine import RuleEngine
from src.extractors.keyword_extractor import KeywordExtractor
from src.config.config import ConfigLoader

# 测试的sitemap URL列表
TEST_SITEMAPS = [
    "https://www.pixelcut.ai/sitemap.xml",
    "https://sitemap.canva.com/sitemap_index.xml",
    "https://www.fotor.com/sitemaps/v2/index.xml",
    "https://www.freepik.es/sitemap-ai.xml",
    "https://www.aragon.ai/sitemap.xml",
    "https://www.insmind.com/sitemap.xml",
    "https://www.fluxpro.ai/sitemap.xml",
    "https://fluxproweb.com/sitemap.xml",
    "https://airbrush.com/sitemap.xml",
    "https://www.cutout.pro/sitemap.xml",
    "https://pollo.ai/sitemap.xml",
    "https://www.logoai.com/sitemap.xml",
    "https://stockimg.ai/sitemap.xml",
    "https://getimg.ai/sitemap.xml",
    "https://flair.ai/sitemap.xml",
    "https://www.media.io/sitemap.xml",
    "https://www.chromastudio.ai/sitemap.xml",
    "https://fal.ai/sitemap.xml",
    "https://venngage.com/sitemap.xml",
    "https://venngage.com/sitemap-ai-tools.xml",
    "https://monica.im/sitemap.xml",
    "https://www.visme.co/sitemap.xml",
    "https://looka.com/sitemap_index.xml",
    "https://www.appointo.me/sitemap.xml",
    "https://media.io/sitemap_index.xml",
    "https://pica-ai.com/sitemap.xml",
    "https://photoroom.com/sitemap.xml",
    "https://magicstudio.com/sitemap_news.xml",
    "https://imgupscaler.com/sitemap.xml",
    "https://magicstudio.com/sitemap.xml",
    "https://www.clipfly.ai/sitemap.xml",
    "https://www.heygen.com/sitemap.xml",
    "https://fliki.ai/sitemap.xml",
    "https://www.imgkits.com/sitemap_index.xml",
    "https://imglarger.com/sitemap.xml",
    "https://higgsfield.cc/sitemap.xml",
    "https://www.imagine.art/sitemap.xml",
    "https://unrealspeech.com/sitemap.xml"
]

async def extract_with_rules():
    """使用规则引擎提取所有sitemap URL和关键词"""
    
    print("=" * 80)
    print("完整Sitemap URL提取（规则引擎版）")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"站点数: {len(TEST_SITEMAPS)}")
    print("=" * 80)
    
    # 加载配置和规则
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    rules_path = Path(__file__).parent / 'config' / 'url_rules.yaml'
    
    config_loader = ConfigLoader(str(config_path), str(rules_path))
    
    # 尝试加载配置（可能失败）
    try:
        config = config_loader.load_system_config()
        print("✅ 配置加载成功")
    except Exception as e:
        print(f"⚠️ 配置加载失败（继续使用规则）: {str(e)[:100]}...")
    
    # 加载规则
    rules = config_loader.load_url_rules()
    print(f"✅ 加载了 {len(rules)} 个域名规则")
    
    # 初始化规则引擎
    rule_engine = RuleEngine(rules)
    
    # 初始化关键词提取器
    keyword_extractor = KeywordExtractor()
    
    # 创建aiohttp session
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=10)
    session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    
    # 输出文件
    output_file = f'all_urls_with_rules_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    try:
        # 初始化解析器
        parser = SitemapParser(
            session=session,
            max_depth=2
        )
        
        # 打开输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入头部信息
            f.write(f"# Sitemap URL提取结果（使用规则引擎）\n")
            f.write(f"# 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 站点: {', '.join(TEST_SITEMAPS)}\n")
            f.write(f"# 格式: URL | 关键词 | 状态 | 使用规则\n")
            f.write("=" * 100 + "\n\n")
            
            # 统计数据
            total_urls_all = 0
            total_filtered = 0
            total_extracted = 0
            
            for sitemap_url in TEST_SITEMAPS:
                print(f"\n处理: {sitemap_url}")
                print("-" * 60)
                
                f.write(f"\n## {sitemap_url}\n")
                f.write("-" * 80 + "\n")
                
                try:
                    # 1. 解析sitemap获取URL列表
                    print(f"正在解析sitemap...")
                    urls = await parser.parse_sitemap(sitemap_url)
                    print(f"找到 {len(urls)} 个URL")
                    
                    site_total = len(urls)
                    site_filtered = 0
                    site_extracted = 0
                    
                    if not urls:
                        f.write("未找到任何URL\n")
                        continue
                    
                    # 2. 处理每个URL
                    print(f"正在处理URL...")
                    for idx, url in enumerate(urls, 1):
                        if idx % 100 == 0:
                            print(f"  已处理: {idx}/{len(urls)}")
                        
                        # 获取URL规则
                        url_rule = rule_engine.get_rule_for_url(url)
                        rule_domain = url_rule.domain if url_rule else "默认"
                        
                        # 解析URL
                        parsed = urlparse(url)
                        path = parsed.path
                        
                        # 检查是否应该被过滤
                        is_filtered = False
                        if url_rule and url_rule.exclude_patterns:
                            import re
                            for pattern in url_rule.exclude_patterns:
                                if re.search(pattern, path):
                                    is_filtered = True
                                    site_filtered += 1
                                    break
                        
                        # 提取关键词
                        keywords = ""
                        if not is_filtered:
                            # 移除末尾的斜杠
                            path = path.rstrip('/')
                            if path:
                                # 获取最后的路径段
                                last_segment = path.split('/')[-1] if '/' in path else path
                                
                                if last_segment:
                                    # 移除文件扩展名
                                    if '.' in last_segment:
                                        last_segment = last_segment.rsplit('.', 1)[0]
                                    
                                    # 将连字符和下划线替换为空格
                                    last_segment = last_segment.replace('-', ' ').replace('_', ' ')
                                    
                                    # 清理特殊字符
                                    keywords = keyword_extractor.processor.clean_keyword(last_segment)
                                    if keywords:
                                        site_extracted += 1
                        
                        # 写入结果（只在测试模式下写入前50个）
                        if idx <= 50:  # 只记录前50个作为示例
                            status = "已过滤" if is_filtered else "正常"
                            f.write(f"{url} | {keywords} | {status} | {rule_domain}\n")
                    
                    # 站点统计
                    f.write(f"\n站点统计: 总计={site_total}, 已过滤={site_filtered}, 成功提取={site_extracted}\n")
                    
                    total_urls_all += site_total
                    total_filtered += site_filtered
                    total_extracted += site_extracted
                    
                    print(f"站点完成: 总计={site_total}, 已过滤={site_filtered}, 成功提取={site_extracted}")
                    
                except Exception as e:
                    error_msg = f"处理失败: {str(e)}"
                    print(f"❌ {error_msg}")
                    f.write(f"\n错误: {error_msg}\n")
                    import traceback
                    traceback.print_exc()
            
            # 写入总体统计
            f.write("\n" + "=" * 100 + "\n")
            f.write("## 总体统计\n")
            f.write(f"- 总URL数: {total_urls_all}\n")
            f.write(f"- 已过滤数: {total_filtered}\n")
            f.write(f"- 未过滤数: {total_urls_all - total_filtered}\n")
            f.write(f"- 成功提取关键词: {total_extracted}\n")
            if total_urls_all > 0:
                f.write(f"- 过滤率: {total_filtered/total_urls_all*100:.1f}%\n")
            if (total_urls_all - total_filtered) > 0:
                f.write(f"- 提取率: {total_extracted/(total_urls_all-total_filtered)*100:.1f}% (基于未过滤URL)\n")
        
        print(f"\n{'='*80}")
        print(f"✅ 提取完成!")
        print(f"📁 结果已保存到: {output_file}")
        print(f"📊 总计: {total_urls_all} URLs")
        print(f"   - 已过滤: {total_filtered}")
        print(f"   - 成功提取: {total_extracted}")
        print("="*80)
        
    finally:
        # 关闭session
        await session.close()

if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(extract_with_rules())