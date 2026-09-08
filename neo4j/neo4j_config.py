import sys
from pathlib import Path
from typing import Optional

# 自动处理路径问题
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from config.get_config import load_env_config



def neo4j_connection( env: Optional[str] = None):
    """
    获取数据库链接信息

    Args:
        env: 可选，手动指定环境名称
    
    Returns:
        链接信息

    """
    configs = load_env_config(env)
    config = configs["config"] if configs else None
    neo4j_info = config["neo4j"]
    url = f"{neo4j_info['url_prefix']}://{neo4j_info['host']}:{neo4j_info['port']}"
    neo4j_info['url'] = neo4j_info.get("url",url)

    return neo4j_info


if __name__ == "__main__":
    print(neo4j_connection("local"))