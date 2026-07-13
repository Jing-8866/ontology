import os
import yaml


class ConfigManager:
    """多环境配置管理器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = os.path.join(os.path.dirname(__file__), config_dir)
        self._config = None

    def _load_yaml(self, filename: str) -> dict:
        path = os.path.join(self.config_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load(self) -> dict:
        """加载配置（自动识别环境）"""
        # 1. 读取主配置
        main_cfg = self._load_yaml("config.yaml")

        # 2. 确定环境（环境变量 > 配置文件）
        env = os.getenv("APP_ENV") or main_cfg.get("current_env", "dev")

        # 3. 加载环境配置
        env_filename = f"config-{env}.yaml"
        env_cfg = self._load_yaml(env_filename)

        self._config = {
            "env": env,
            **env_cfg,
        }
        return self._config

    def get(self, key: str, default=None):
        """安全读取配置项"""
        return self._config.get(key, default)



if __name__ == "__main__":
    config_manager = ConfigManager()
    cfg = config_manager.load()

    print("当前环境:", cfg["env"])
    print("日志级别:", cfg.get("log_level"))

    # print(cfg.get("ai_api_list", {})["ds_flash"])
    # print(cfg.get("ai_api_list", {}).get("ds_flash").get("model_name"))



    # # 读取 AI 模型配置
    # for model_name, model_cfg in cfg.get("ai_api_list", {}).items():
    #     print(f"\n模型: {model_name}")
    #     print(f"  模型: {model_cfg['model_name']}")
    #     print(f"  Base URL: {model_cfg['base_url']}")
    #     print(f"  模型: {model_cfg['apiKey']}")

    # # 读取数据库配置
    # db = cfg.get("database", {}).get("mysql", {})
    # print("\n数据库配置:")
    # print(f"  Host: {db.get('host')}")
    # print(f"  Port: {db.get('port')}")