
import os
import json

import yaml
from pathlib import Path
from typing import Any, Optional


BASE_DIR = Path(__file__).resolve().parent 
BASE_FILE = "config.yml"
CONFIG_PATH = BASE_DIR / BASE_FILE

GAP_NUMBER = 30 # 链接符数量

def load_main_config() -> dict[str, Any]:
    """加载主配置文件 config.yml"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"主配置文件不存在: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_current_env() -> str:
    """
    获取当前运行环境
    
    优先级：
    1. 环境变量 ENV
    2. 环境变量 APP_ENV
    3. 默认为 config.yml 中的 default_env
    4. 若 config.yml 中未指定 default_env，则默认为 dev
    
    Returns:
        str: 环境名称 (dev/prod)
    """
    env = os.environ.get("ENV") or os.environ.get("APP_ENV")
    
    if env:
        # 规范化环境名称
        if env.lower() in ("prod", "production"):
            return "prod"
        elif env.lower() in ("dev", "development"):
            return "dev"
    
    return "dev"  # 默认值


def load_env_config(env: Optional[str] = None) -> dict[str, Any]:
    """
    根据环境加载对应的配置文件
    
    流程：
    1. 加载 config.yml 获取环境映射
    2. 根据环境变量确定当前环境
    3. 加载对应环境的配置文件
    
    Args:
        env: 可选，手动指定环境名称
        
    Returns:
        dict: 环境配置内容
    """
    # 1. 加载主配置文件
    main_config = load_main_config()
    
    # 2. 确定目标环境
    # target_env = env or get_current_env()
    target_env = env


    
    # 3. 获取对应的配置文件名
    env_configs = main_config.get("environments", {})
    config_file = env_configs.get(target_env)
    
    if not config_file:
        # 如果找不到对应环境，使用默认环境
        default_env = main_config.get("default_env", "")
        config_file = env_configs.get(default_env, None)
        
        if not config_file:
            print("*" * GAP_NUMBER)
            print(f">>> 不存在【{default_env}】环境")
            print("*" * GAP_NUMBER)
            return

        target_env = default_env
    
    # 4. 加载环境配置文件
    config_path = BASE_DIR / config_file
    if not config_path.exists():
        print (f">>> 环境配置文件不存在: {config_path}")
        return
    
    # print(f">>> 【{target_env}】加载配置文件: {config_file}")
    print(f">>> 加载【{target_env}】环境配置文件")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return {"environment": target_env,"config": yaml.safe_load(f)}


if __name__ == "__main__":
    rst = load_env_config()
    
    msg = rst["config"]

    kvs = rst["config"].keys()
    print()
    node = "description"
    # print(msg["neo4j"])
    for k in kvs:
        v = msg[k]
        print(f">>> {k}: {v}")
        print()

