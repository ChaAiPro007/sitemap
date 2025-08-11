"""
环境变量加载器
支持多种环境和路径独立加载
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, List
from dotenv import load_dotenv
import logging


class EnvVariableError(Exception):
    """环境变量错误"""
    pass


class EnhancedEnvLoader:
    """环境变量加载器"""
    
    # 必需的环境变量
    REQUIRED_VARS = {
        'SITEMAP_API_URL': 'Sitemap关键词提交API地址',
        'SITEMAP_SECRET_KEY': 'Sitemap API认证密钥',
        'SITEMAP_URLS': '要监控的sitemap URL列表',
        'ENCRYPTION_KEY': '数据加密密钥（66字符）'
    }
    
    # 可选环境变量
    OPTIONAL_VARS = {
        'LOG_LEVEL': 'INFO',
        'DEBUG_MODE': 'false',
        'GITHUB_ACTIONS': None
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化环境变量加载器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.env_loaded = False
        self.found_env_file = None
        
    def load_environment(self) -> bool:
        """
        加载环境变量文件
        
        Returns:
            bool: 是否成功加载环境文件
        """
        if self.env_loaded:
            return True
            
        # CI环境检测
        if self._is_ci_environment():
            self.logger.info("检测到CI环境，使用系统环境变量")
            self.env_loaded = True
            return True
            
        # 尝试多个.env文件路径
        env_paths = self._get_env_file_paths()
        
        for env_path in env_paths:
            if env_path.exists():
                try:
                    abs_path = env_path.resolve()
                    result = load_dotenv(dotenv_path=abs_path, override=True)
                    if result:
                        self.found_env_file = str(abs_path)
                        self.logger.info(f"成功加载环境文件: {abs_path}")
                        self.env_loaded = True
                        return True
                except Exception as e:
                    self.logger.warning(f"加载环境文件失败: {env_path} - {e}")
                    
        # 检查必需的环境变量是否已设置
        missing_vars = self._check_required_vars()
        if not missing_vars:
            self.logger.info("未找到.env文件，但所有必需环境变量已设置")
            self.env_loaded = True
            return True
            
        self.logger.warning("未找到.env文件且缺少必需的环境变量")
        return False
        
    def _is_ci_environment(self) -> bool:
        """
        检测是否在CI环境中运行
        
        Returns:
            bool: 是否在CI环境中
        """
        ci_indicators = [
            'GITHUB_ACTIONS',
            'CI',
            'CONTINUOUS_INTEGRATION',
            'JENKINS_HOME',
            'GITLAB_CI',
            'CIRCLECI',
            'TRAVIS'
        ]
        return any(os.getenv(indicator) for indicator in ci_indicators)
        
    def _get_env_file_paths(self) -> List[Path]:
        """
        获取可能的.env文件路径列表
        
        Returns:
            List[Path]: 可能的.env文件路径
        """
        paths = []
        
        # 1. 当前工作目录
        paths.append(Path.cwd() / '.env')
        
        # 2. 脚本所在目录
        if hasattr(sys, 'argv') and sys.argv:
            script_path = Path(sys.argv[0]).resolve()
            if script_path.is_file():
                paths.append(script_path.parent / '.env')
                
        # 3. 项目根目录（通过标记文件查找）
        project_root = self._find_project_root()
        if project_root:
            paths.append(project_root / '.env')
            
        # 4. GitHub Actions工作空间
        github_workspace = os.getenv('GITHUB_WORKSPACE')
        if github_workspace:
            paths.append(Path(github_workspace) / '.env')
            
        # 去重并返回
        unique_paths = []
        seen = set()
        for path in paths:
            abs_path = path.resolve()
            if abs_path not in seen:
                unique_paths.append(path)
                seen.add(abs_path)
                
        return unique_paths
        
    def _find_project_root(self) -> Optional[Path]:
        """
        查找项目根目录
        
        Returns:
            Optional[Path]: 项目根目录路径
        """
        # 项目根目录标记文件
        markers = [
            'requirements.txt',
            'pyproject.toml',
            'setup.py',
            'main.py',
            '.git',
            'README.md'
        ]
        
        current = Path.cwd()
        
        # 向上查找最多10层
        for _ in range(10):
            for marker in markers:
                if (current / marker).exists():
                    return current
            
            parent = current.parent
            if parent == current:
                break
            current = parent
            
        return None
        
    def _check_required_vars(self) -> List[str]:
        """
        检查必需的环境变量
        
        Returns:
            List[str]: 缺失的环境变量列表
        """
        missing = []
        for var_name in self.REQUIRED_VARS:
            if not os.getenv(var_name):
                missing.append(var_name)
        return missing
        
    def validate_environment(self) -> Dict[str, any]:
        """
        验证环境变量配置
        
        Returns:
            Dict: 验证结果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'variables': {}
        }
        
        # 检查必需变量
        for var_name, description in self.REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value:
                result['valid'] = False
                result['errors'].append(f"缺少必需的环境变量: {var_name} ({description})")
                result['variables'][var_name] = {'status': 'missing', 'description': description}
            else:
                # 验证格式
                if var_name == 'SITEMAP_API_URL':
                    if not (value.startswith('http://') or value.startswith('https://')):
                        result['warnings'].append(f"{var_name} 应该以 http:// 或 https:// 开头")
                elif var_name == 'ENCRYPTION_KEY':
                    if len(value) < 32:
                        result['warnings'].append(f"{var_name} 长度应至少为32字符，推荐66字符")
                        
                result['variables'][var_name] = {
                    'status': 'set',
                    'description': description,
                    'length': len(value)
                }
                
        return result
        
    def get_status(self) -> Dict[str, any]:
        """
        获取环境加载状态
        
        Returns:
            Dict: 状态信息
        """
        return {
            'loaded': self.env_loaded,
            'env_file': self.found_env_file,
            'is_ci': self._is_ci_environment(),
            'is_github_actions': bool(os.getenv('GITHUB_ACTIONS'))
        }


def get_env_var(name: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
    """
    获取环境变量值
    
    Args:
        name: 环境变量名
        default: 默认值
        required: 是否必需
        
    Returns:
        Optional[str]: 环境变量值
        
    Raises:
        EnvVariableError: 当必需的环境变量缺失时
    """
    value = os.getenv(name, default)
    
    if required and not value:
        raise EnvVariableError(f"必需的环境变量 {name} 未设置")
        
    return value


def ensure_env_loaded(logger: Optional[logging.Logger] = None) -> EnhancedEnvLoader:
    """
    确保环境变量已加载
    
    Args:
        logger: 日志记录器
        
    Returns:
        EnhancedEnvLoader: 环境加载器实例
    """
    loader = EnhancedEnvLoader(logger)
    loader.load_environment()
    return loader