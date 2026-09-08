#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j 工具模块 - 支持数据库管理和用户管理
"""

from neo4j import GraphDatabase
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from functools import wraps
from enum import Enum

import neo4j_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

neo4j_con = neo4j_config.neo4j_connection("local")

CONFIG = {
    "user": neo4j_con.get("username", ""),
    "password": neo4j_con.get("password", ""),
    "default_database": neo4j_con.get("default_database", "neo4j"),
    "url": neo4j_con.get("url", f"{neo4j_con['url_prefix']}://{neo4j_con['host']}:{neo4j_con['port']}")
}


class DatabaseRole(Enum):
    """Neo4j 内置角色"""
    ADMIN = "admin"
    READER = "reader"
    EDITOR = "editor"
    ARCHITECT = "architect"
    PUBLISHER = "publisher"


class Neo4jManager:
    """Neo4j 管理类 - 处理数据库和用户管理"""
    
    def __init__(self, url: str, user: str, password: str):
        self.url = url
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(url, auth=(user, password))
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def _execute_in_system(self, cypher: str, **kwargs) -> List[Dict[str, Any]]:
        """在 system 数据库执行管理语句"""
        with self.driver.session(database="system") as session:
            logger.info(f"执行系统管理语句: {cypher}")
            result = session.run(cypher, kwargs)
            return [record.data() for record in result]
    
    # ==================== 数据库管理 ====================
    
    def create_database(self, name: str, if_not_exists: bool = True) -> bool:
        """创建数据库"""
        try:
            cypher = f"CREATE DATABASE {name}"
            if if_not_exists:
                cypher += " IF NOT EXISTS"
            self._execute_in_system(cypher)
            logger.info(f"✅ 数据库 '{name}' 创建成功")
            return True
        except Exception as e:
            logger.error(f"❌ 创建数据库 '{name}' 失败: {e}")
            return False
    
    def drop_database(self, name: str, if_exists: bool = True) -> bool:
        """删除数据库"""
        try:
            cypher = f"DROP DATABASE {name}"
            if if_exists:
                cypher += " IF EXISTS"
            self._execute_in_system(cypher)
            logger.info(f"✅ 数据库 '{name}' 删除成功")
            return True
        except Exception as e:
            logger.error(f"❌ 删除数据库 '{name}' 失败: {e}")
            return False
    
    def start_database(self, name: str) -> bool:
        """启动数据库"""
        try:
            self._execute_in_system(f"START DATABASE {name}")
            logger.info(f"✅ 数据库 '{name}' 启动成功")
            return True
        except Exception as e:
            logger.error(f"❌ 启动数据库 '{name}' 失败: {e}")
            return False
    
    def stop_database(self, name: str) -> bool:
        """停止数据库"""
        try:
            self._execute_in_system(f"STOP DATABASE {name}")
            logger.info(f"✅ 数据库 '{name}' 停止成功")
            return True
        except Exception as e:
            logger.error(f"❌ 停止数据库 '{name}' 失败: {e}")
            return False
    
    def list_databases(self) -> List[Dict[str, Any]]:
        """列出所有数据库"""
        return self._execute_in_system("SHOW DATABASES")
    
    def database_exists(self, name: str) -> bool:
        """检查数据库是否存在"""
        databases = self.list_databases()
        return any(db['name'] == name for db in databases)
    
    def get_database_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取数据库详细信息"""
        databases = self.list_databases()
        for db in databases:
            if db['name'] == name:
                return db
        return None
    
    # ==================== 用户管理 ====================
    
    def create_user(self, username: str, password: str, 
                   change_required: bool = True,
                   status: str = "ACTIVE") -> bool:
        """
        创建用户
        
        :param username: 用户名
        :param password: 密码
        :param change_required: 是否要求首次登录改密码
        :param status: 用户状态 ACTIVE/SUSPENDED
        """
        try:
            cypher = f"CREATE USER {username} SET PASSWORD $password"
            if change_required:
                cypher += " CHANGE REQUIRED"
            cypher += f" SET STATUS {status}"
            
            self._execute_in_system(cypher, password=password)
            logger.info(f"✅ 用户 '{username}' 创建成功")
            return True
        except Exception as e:
            logger.error(f"❌ 创建用户 '{username}' 失败: {e}")
            return False
    
    def drop_user(self, username: str, if_exists: bool = True) -> bool:
        """删除用户"""
        try:
            cypher = f"DROP USER {username}"
            if if_exists:
                cypher += " IF EXISTS"
            self._execute_in_system(cypher)
            logger.info(f"✅ 用户 '{username}' 删除成功")
            return True
        except Exception as e:
            logger.error(f"❌ 删除用户 '{username}' 失败: {e}")
            return False
    
    def alter_user_password(self, username: str, new_password: str,
                           change_required: bool = False) -> bool:
        """修改用户密码"""
        try:
            cypher = f"ALTER USER {username} SET PASSWORD $password"
            if change_required:
                cypher += " CHANGE REQUIRED"
            
            self._execute_in_system(cypher, password=new_password)
            logger.info(f"✅ 用户 '{username}' 密码修改成功")
            return True
        except Exception as e:
            logger.error(f"❌ 修改用户 '{username}' 密码失败: {e}")
            return False
    
    def alter_user_status(self, username: str, status: str = "ACTIVE") -> bool:
        """
        修改用户状态
        
        :param status: ACTIVE 或 SUSPENDED
        """
        try:
            status = status.upper()
            if status not in ["ACTIVE", "SUSPENDED"]:
                raise ValueError("状态必须是 ACTIVE 或 SUSPENDED")
            
            self._execute_in_system(f"ALTER USER {username} SET STATUS {status}")
            logger.info(f"✅ 用户 '{username}' 状态已设为 {status}")
            return True
        except Exception as e:
            logger.error(f"❌ 修改用户 '{username}' 状态失败: {e}")
            return False
    
    def list_users(self) -> List[Dict[str, Any]]:
        """列出所有用户"""
        return self._execute_in_system("SHOW USERS")
    
    def user_exists(self, username: str) -> bool:
        """检查用户是否存在"""
        users = self.list_users()
        return any(user['user'] == username for user in users)
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户详细信息"""
        users = self.list_users()
        for user in users:
            if user['user'] == username:
                return user
        return None
    
    # ==================== 角色和权限管理 ====================
    
    def grant_role(self, username: str, role: Union[str, DatabaseRole]) -> bool:
        """为用户分配角色"""
        if isinstance(role, DatabaseRole):
            role = role.value
        try:
            self._execute_in_system(f"GRANT ROLE {role} TO {username}")
            logger.info(f"✅ 已将角色 '{role}' 授予用户 '{username}'")
            return True
        except Exception as e:
            logger.error(f"❌ 授予角色失败: {e}")
            return False
    
    def revoke_role(self, username: str, role: Union[str, DatabaseRole]) -> bool:
        """撤销用户角色"""
        if isinstance(role, DatabaseRole):
            role = role.value
        try:
            self._execute_in_system(f"REVOKE ROLE {role} FROM {username}")
            logger.info(f"✅ 已从用户 '{username}' 撤销角色 '{role}'")
            return True
        except Exception as e:
            logger.error(f"❌ 撤销角色失败: {e}")
            return False
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """列出所有角色"""
        return self._execute_in_system("SHOW ROLES")
    
    def list_user_privileges(self, username: str = None) -> List[Dict[str, Any]]:
        """列出用户权限"""
        if username:
            return self._execute_in_system(f"SHOW USER {username} PRIVILEGES")
        return self._execute_in_system("SHOW USER PRIVILEGES")
    
    def create_role(self, role_name: str) -> bool:
        """创建自定义角色"""
        try:
            self._execute_in_system(f"CREATE ROLE {role_name}")
            logger.info(f"✅ 角色 '{role_name}' 创建成功")
            return True
        except Exception as e:
            logger.error(f"❌ 创建角色失败: {e}")
            return False
    
    def drop_role(self, role_name: str) -> bool:
        """删除角色"""
        try:
            self._execute_in_system(f"DROP ROLE {role_name}")
            logger.info(f"✅ 角色 '{role_name}' 删除成功")
            return True
        except Exception as e:
            logger.error(f"❌ 删除角色失败: {e}")
            return False
    
    # ==================== 数据库权限控制 ====================
    
    def grant_database_access(self, username: str, database: str = "*") -> bool:
        """授予数据库访问权限"""
        try:
            self._execute_in_system(f"GRANT ACCESS ON DATABASE {database} TO {username}")
            logger.info(f"✅ 已授予用户 '{username}' 对数据库 '{database}' 的访问权限")
            return True
        except Exception as e:
            logger.error(f"❌ 授予数据库访问权限失败: {e}")
            return False
    
    def grant_read_access(self, username: str, database: str = "*") -> bool:
        """授予数据库读权限"""
        try:
            self._execute_in_system(f"GRANT READ ON GRAPH {database} TO {username}")
            logger.info(f"✅ 已授予用户 '{username}' 对数据库 '{database}' 的读权限")
            return True
        except Exception as e:
            logger.error(f"❌ 授予读权限失败: {e}")
            return False
    
    def grant_write_access(self, username: str, database: str = "*") -> bool:
        """授予数据库写权限"""
        try:
            self._execute_in_system(f"GRANT WRITE ON GRAPH {database} TO {username}")
            logger.info(f"✅ 已授予用户 '{username}' 对数据库 '{database}' 的写权限")
            return True
        except Exception as e:
            logger.error(f"❌ 授予写权限失败: {e}")
            return False


class CypherExecutor:
    """Cypher 查询执行器"""
    
    def __init__(self, url: str = CONFIG["url"], user: str = CONFIG["user"], 
                 password: str = CONFIG["password"], database: str = CONFIG["default_database"]):
        self.url = url
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        self.manager = None
        
        try:
            self.driver = GraphDatabase.driver(url, auth=(user, password))
            self.manager = Neo4jManager(url, user, password)
            logger.info(f"成功创建到 {url} 的连接驱动")
        except Exception as e:
            logger.error(f"创建连接驱动失败: {e}")
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
        if self.manager:
            self.manager.close()
    
    def _build_params(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """构建参数映射"""
        params = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                params.update(arg)
            else:
                params[f"{i}"] = arg
        params.update(kwargs)
        return params
    
    def _is_management_statement(self, cypher: str) -> bool:
        """判断是否为管理语句"""
        management_statements = [
            "CREATE DATABASE", "DROP DATABASE", "START DATABASE", "STOP DATABASE",
            "SHOW DATABASES", "SHOW USERS", "CREATE USER", "DROP USER", "ALTER USER",
            "GRANT", "REVOKE", "DENY", "SHOW PRIVILEGES", "SHOW ROLES",
            "CREATE ROLE", "DROP ROLE"
        ]
        upper_cypher = cypher.strip().upper()
        return any(upper_cypher.startswith(stmt) for stmt in management_statements)
    
    def execute_cypher(self, cypher: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        通用Cypher查询执行函数
        
        自动识别管理语句并在 system 数据库执行
        """
        try:
            # 判断是否是管理语句
            if self._is_management_statement(cypher):
                logger.info(f"检测到管理语句，在 system 数据库执行")
                params = self._build_params(args, kwargs)
                with self.driver.session(database="system") as session:
                    result = session.run(cypher, params)
                    return [record.data() for record in result]
            
            # 普通查询
            with self.driver.session(database=self.database) as session:
                params = self._build_params(args, kwargs)
                logger.info(f"执行查询: {cypher}")
                logger.info(f"参数: {params}")
                result = session.run(cypher, params)
                return [record.data() for record in result]
                
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise


# ============ 全局实例管理 ============

_executor_instance = None

def get_executor(url: str = CONFIG["url"], user: str = CONFIG["user"], 
                 password: str = CONFIG["password"], 
                 database: str = CONFIG["default_database"]) -> CypherExecutor:
    """获取或创建执行器实例"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = CypherExecutor(url, user, password, database)
    return _executor_instance

def run_cypher(cypher: str, *args, **kwargs) -> List[Dict[str, Any]]:
    """统一入口函数"""
    executor = get_executor()
    return executor.execute_cypher(cypher, *args, **kwargs)

def init_neo4j(url: str = CONFIG["url"], user: str = CONFIG["user"], 
               password: str = CONFIG["password"], 
               database: str = CONFIG["default_database"]):
    """初始化连接"""
    global _executor_instance
    _executor_instance = CypherExecutor(url, user, password, database)
    return _executor_instance

def close_neo4j():
    """关闭连接"""
    global _executor_instance
    if _executor_instance:
        _executor_instance.close()
        _executor_instance = None

def get_manager() -> Neo4jManager:
    """获取管理器实例"""
    executor = get_executor()
    return executor.manager


# ============ 便捷函数 ============

# 数据库管理便捷函数
def create_database(name: str, if_not_exists: bool = True) -> bool:
    return get_manager().create_database(name, if_not_exists)

def drop_database(name: str, if_exists: bool = True) -> bool:
    return get_manager().drop_database(name, if_exists)

def list_databases() -> List[Dict[str, Any]]:
    return get_manager().list_databases()

# 用户管理便捷函数
def create_user(username: str, password: str, role: str = None,
               change_required: bool = True) -> bool:
    manager = get_manager()
    if manager.create_user(username, password, change_required):
        if role:
            manager.grant_role(username, role)
        return True
    return False

def drop_user(username: str) -> bool:
    return get_manager().drop_user(username)

def list_users() -> List[Dict[str, Any]]:
    return get_manager().list_users()

def alter_user_password(username: str, new_password: str) -> bool:
    return get_manager().alter_user_password(username, new_password)

def alter_user_status(username: str, status: str) -> bool:
    return get_manager().alter_user_status(username, status)

def grant_role(username: str, role: str) -> bool:
    return get_manager().grant_role(username, role)

def revoke_role(username: str, role: str) -> bool:
    return get_manager().revoke_role(username, role)


# ============ 装饰器和上下文管理器 ============

def with_neo4j(func):
    """装饰器：自动注入会话"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        executor = get_executor()
        with executor.driver.session(database=executor.database) as session:
            return func(session, *args, **kwargs)
    return wrapper

class Neo4jConnection:
    """上下文管理器"""
    def __init__(self, url: str = CONFIG["url"], user: str = CONFIG["user"], 
                 password: str = CONFIG["password"], 
                 database: str = CONFIG["default_database"]):
        self.executor = CypherExecutor(url, user, password, database)
    
    def __enter__(self):
        return self.executor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.close()


# ============ 使用示例 ============

def demo_management():
    """演示管理功能"""
    
    print("="*60)
    print("Neo4j 管理功能演示")
    print("="*60)
    
    # 初始化连接
    init_neo4j()
    
    try:
        # ===== 数据库管理 =====
        print("\n📦 数据库管理")
        print("-"*40)
        
        # 创建数据库
        create_database("test_db")
        
        # 列出数据库
        dbs = list_databases()
        print("数据库列表:")
        for db in dbs:
            print(f"  - {db['name']} (状态: {db.get('currentStatus', 'unknown')})")
        
        # 检查数据库是否存在
        exists = get_manager().database_exists("test_db")
        print(f"test_db 存在: {exists}")
        
        # ===== 用户管理 =====
        print("\n👤 用户管理")
        print("-"*40)
        
        # 创建用户并分配角色
        create_user("analyst", "Password123!", role="reader")
        
        # 列出用户
        users = list_users()
        print("用户列表:")
        for user in users:
            print(f"  - {user['user']} (状态: {user.get('status', 'unknown')})")
        
        # 修改用户密码
        alter_user_password("analyst", "NewPass456!")
        
        # 升级用户角色
        grant_role("analyst", "editor")
        
        # 查看用户权限
        privileges = get_manager().list_user_privileges("analyst")
        print(f"analyst 的权限:")
        for p in privileges:
            print(f"  - {p}")
        
        # ===== 清理 =====
        print("\n🧹 清理")
        print("-"*40)
        
        # 删除用户
        drop_user("analyst")
        
        # 删除数据库
        drop_database("test_db")
        
        print("\n✅ 演示完成")
        
    finally:
        close_neo4j()


def demo_advanced_usage():
    """演示高级用法"""
    
    print("\n" + "="*60)
    print("高级用法演示")
    print("="*60)
    
    # 1. 创建完整的环境
    init_neo4j()
    
    try:
        manager = get_manager()
        
        # 创建数据库
        manager.create_database("business_db")
        
        # 创建用户并分配精细权限
        manager.create_user("data_analyst", "SecurePass789!")
        manager.grant_role("data_analyst", "reader")
        manager.grant_database_access("data_analyst", "business_db")
        manager.grant_read_access("data_analyst", "business_db")
        
        # 创建另一个用户
        manager.create_user("data_admin", "AdminPass123!", change_required=False)
        manager.grant_role("data_admin", "admin")
        
        # 查看所有角色
        roles = manager.list_roles()
        print("\n可用角色:")
        for role in roles:
            print(f"  - {role['role']}")
        
        # 在业务数据库中执行查询
        run_cypher("CREATE (n:Company {name: 'ACME Corp'}) RETURN n")
        
        # 查询数据
        result = run_cypher("MATCH (n) RETURN n LIMIT 10")
        print(f"\n查询结果: {result}")
        
        # 清理
        print("\n清理测试数据...")
        manager.drop_user("data_analyst")
        manager.drop_user("data_admin")
        manager.drop_database("business_db")
        
        print("✅ 高级演示完成")
        
    finally:
        close_neo4j()


if __name__ == "__main__":
    # 运行演示
    demo_management()
    demo_advanced_usage()