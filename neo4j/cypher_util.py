from neo4j import GraphDatabase
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from functools import wraps

import neo4j_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

neo4j_con = neo4j_config.neo4j_connection("local")

CONFIG = {
    "user": neo4j_con.get("username", ""),
    "password": neo4j_con.get("password", ""),
    "default_database": neo4j_con.get("default_database", ""),
    "uri": neo4j_con.get("uri", f"{neo4j_con['url_prefix']}://{neo4j_con['host']}:{neo4j_con['port']}")
}


class CypherExecutor:
    def __init__(self, uri: str = CONFIG["uri"], user: str = CONFIG["user"], password: str = CONFIG["password"], database: str = CONFIG["default_database"]):
        """
        初始化Neo4j连接
        
        :param uri: 连接地址，如 bolt://localhost:7687
        :param user: 用户名
        :param password: 密码
        :param database: 数据库名称，默认neo4j
        """
        # self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        # logging.basicConfig(level=logging.INFO)
        
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"成功创建到 {uri} 的连接驱动")
        except Exception as e:
            logger.error(f"创建连接驱动失败: {e}")
        
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def _build_params(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """
        构建参数映射 - 统一处理各种参数格式
        
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 合并后的参数字典
        """
        params = {}
        
        # 处理位置参数
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                # 如果位置参数是字典，直接合并
                params.update(arg)
            else:
                # 普通值作为位置参数 $0, $1, $2...
                params[f"{i}"] = arg
        
        # 处理关键字参数
        params.update(kwargs)
        
        return params
    
    def execute_cypher(self, cypher: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        通用Cypher查询执行函数 - 统一入口
        
        支持多种参数传递方式：
        1. 纯位置参数: execute_cypher("...WHERE n.name = $0", "Alice")
        2. 纯关键字参数: execute_cypher("...WHERE n.name = $name", name="Alice")
        3. 混合参数: execute_cypher("...WHERE n.name = $0 AND n.age > $age", "Alice", age=25)
        4. 字典参数: execute_cypher("...WHERE n.name = $name", {"name": "Alice"})
        5. 无参数: execute_cypher("MATCH (n) RETURN n")
        
        :param cypher: Cypher查询语句
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 查询结果列表
        """
        try:
            with self.driver.session(database=self.database) as session:
                # 统一构建参数
                params = self._build_params(args, kwargs)
                
                logging.info(f"Executing Cypher: {cypher}")
                logging.info(f"With parameters: {params}")
                
                result = session.run(cypher, params)
                records = [record.data() for record in result]
                
                return records
                
        except Exception as e:
            logging.error(f"Query execution failed: {e}")
            raise


# ============ 统一入口函数 ============

# 全局执行器实例缓存
_executor_instance = None
_manager_instance = None
def get_executor(uri: str = CONFIG["uri"], user: str = CONFIG["user"], password: str = CONFIG["password"], database: str = CONFIG["default_database"]) -> CypherExecutor:
    """
    获取或创建执行器实例（单例模式）
    """
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = CypherExecutor(uri, user, password, database)
    return _executor_instance

def run_cypher(cypher: str, *args, **kwargs) -> List[Dict[str, Any]]:
    """
    统一入口函数
    
    智能执行 Cypher 语句 - 自动判断在哪个数据库执行
    
    自动识别管理语句并在 system 数据库执行
    
    用法示例：
    >>> run_cypher("MATCH (n:Person) WHERE n.name = $name AND n.age > $age RETURN n", 
                   name="Bob", age=30)
    
    >>> run_cypher("MATCH (n:Person) WHERE n.name = $0 RETURN n", "Alice")
    
    >>> run_cypher("MATCH (n) RETURN n LIMIT 10")
    
    >>> run_cypher("CREATE (n:Person {name: $name, age: $age})", 
                   name="Tom", age=25)
    
    :param cypher: Cypher查询语句
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 查询结果列表
    """
    executor = get_executor()
    return executor.execute_cypher(cypher, *args, **kwargs)

def init_neo4j(uri: str = CONFIG["uri"], user: str = CONFIG["user"], password: str = CONFIG["password"], database: str = CONFIG["default_database"]):
    """
    初始化Neo4j连接配置
    """
    global _executor_instance
    _executor_instance = CypherExecutor(uri, user, password, database)
    return _executor_instance

def close_neo4j():
    """
    关闭Neo4j连接
    """
    global _executor_instance
    if _executor_instance:
        _executor_instance.close()
        _executor_instance = None


# ============ 高级封装 - 装饰器方式 ============

def with_neo4j(func):
    """
    装饰器：自动注入Neo4j会话
    
    用法：
    @with_neo4j
    def my_query(session, name, age):
        return session.run("MATCH (n:Person {name: $name, age: $age}) RETURN n", 
                          name=name, age=age).data()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        executor = get_executor()
        with executor.driver.session(database=executor.database) as session:
            return func(session, *args, **kwargs)
    return wrapper



# ============ 上下文管理器 ============
class Neo4jConnection:
    """上下文管理器方式使用"""
    
    def __init__(self, uri: str = CONFIG["uri"], user: str = CONFIG["user"], password: str = CONFIG["password"], database: str = CONFIG["default_database"]):
        self.executor = CypherExecutor(uri, user, password, database)
    
    def __enter__(self):
        return self.executor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.close()



# ============ 使用示例 ============

def demo_all_usages(database: Optional[str] = None):
    """展示所有调用方式"""
    
    # 1. 初始化连接（通常在应用启动时执行一次）
    # init_neo4j(
    #     uri=CONFIG["uri"],
    #     user=CONFIG["user"],
    #     password=CONFIG["password"],
    #     database=database,
    # )
    
    
    # 方式1：最简单的统一入口函数（推荐）
    print("=== 方式1：统一入口函数 ===")
    
    # 关键字参数
    result1 = run_cypher(
        "MATCH (n:Person) WHERE n.name = $name AND n.age > $age RETURN n",
        name="Bob",
        age=30
    )
    print(f"关键字参数结果: {result1}")
    
    # 位置参数
    result2 = run_cypher(
        "MATCH (n:Person) WHERE n.name = $0 AND n.age > $1 RETURN n",
        "Alice", 25
    )
    print(f"位置参数结果: {result2}")
    
    # 混合参数
    result3 = run_cypher(
        "MATCH (n:Person) WHERE n.name IN $names AND n.age > $min_age AND n.city = $0 RETURN n",
        "New York",
        names=["Alice", "Bob"],
        min_age=20
    )
    print(f"混合参数结果: {result3}")
    
    # 无参数
    result4 = run_cypher("MATCH (n) RETURN n LIMIT 5")
    print(f"无参数结果: {result4}")
    
    # # 创建数据
    # result5 = run_cypher(
    #     "CREATE (n:Person {name: $name, age: $age, city: $city}) RETURN n",
    #     name="Tom",
    #     age=28,
    #     city="Beijing"
    # )
    # print(f"创建结果: {result5}")

    # Merge
    msg_merge = """
    MERGE (u:Person {name: $name})
    ON CREATE SET 
        u.name = $name,
        u.age = $age,
        u.city = $city
    ON MATCH SET 
        u.age = $age,
        u.city = $city
    RETURN u
    """
    rst_merge = run_cypher(msg_merge,
        name="Tom",
        age=28,
        city="Beijing")
    print(f"Merge结果: {rst_merge}")

    
    # 方式2：使用上下文管理器
    print("\n=== 方式2：上下文管理器 ===")
    with Neo4jConnection() as executor:
        result = executor.execute_cypher(
            "MATCH (n:Person) WHERE n.name = $name RETURN n",
            name="Alice"
        )
        print(f"上下文管理器结果: {result}")
    
    # 方式3：使用装饰器
    print("\n=== 方式3：装饰器方式 ===")
    @with_neo4j
    def find_person(session, name):
        return session.run(
            "MATCH (n:Person {name: $name}) RETURN n",
            name=name
        ).data()
    
    result = find_person("Bob")
    print(f"装饰器结果: {result}")
    
    # 关闭连接
    close_neo4j()


# ============ 使用示例 ============

def user_example(database: Optional[str] = CONFIG["default_database"]):
    """使用示例"""
    
    # 1. 初始化连接（通常在应用启动时执行一次）
    init_neo4j(
        uri=CONFIG["uri"],
        user=CONFIG["user"],
        password=CONFIG["password"],
        database=database,
    )
    # uri: str = CONFIG["uri"], user: str = CONFIG["user"], password: str = CONFIG["password"], database: str = CONFIG["default_database"]

    # 2. 到处使用统一入口函数
    # 查询用户
    users = run_cypher(
        "MATCH (u:User {status: $status}) RETURN u.name, u.email",
        status="active"
    )
    
    # 创建关系
    run_cypher(
        """
        MATCH (a:Person {name: $person1})
        MATCH (b:Person {name: $person2})
        CREATE (a)-[:KNOWS {since: $year}]->(b)
        """,
        person1="Alice",
        person2="Bob",
        year=2024
    )
    
    # 批量操作
    for user_data in users_data:
        run_cypher(
            "CREATE (u:User {id: $id, name: $name, email: $email})",
            id=user_data["id"],
            name=user_data["name"],
            email=user_data["email"]
        )
    
    # 3. 程序退出时关闭连接
    close_neo4j()


def add_data(username: str, age: int, city: str,start_date: str, end_date:Optional[str]='9999-12-31', friend_name:Optional[str]=None):
    # Merge
    msg_merge = """
    MERGE (u:Person {name: $username})
    ON CREATE SET 
        u.name = $username,
        u.age = $age
    ON MATCH SET 
        u.age = $age
    
    with u
    MERGE (d:City {name: $city})
    MERGE (u)-[:LIVES_IN {start: date($start_date), end: date($end_date)}]->(d)
    
    with u
    MATCH (f:Person {name: $friend_name})
    MERGE (u)-[:Knows]->(f)
    

    """
    rst_merge = run_cypher(msg_merge,
        username=username,
        age=age,
        city=city,
        start_date=start_date,
        end_date=end_date,
        friend_name=friend_name
        )
    
    # print(f"{username}数据: {rst_merge}")

if __name__ == "__main__":
    # 运行演示
    # add_data("张三", 18, "重庆", "2010-01-01", "2019-12-31", "李四")
    # add_data("张三", 18, "天津", "2020-01-01", "9999-12-31", "李四")

    # add_data("李四", 30, "上海", "2010-01-01", "2019-12-31", "Tom")
    # add_data("李四", 30, "北京", "2020-01-01", "9999-12-31", "Tom")
    
    # add_data("Alice", 28, "重庆", "2010-01-01", "9999-12-31", "张三")
    # add_data("Tom", 26, "北京", "2010-01-01", "9999-12-31", "Alice")

    print("="*30)
    rst = run_cypher("MATCH (data) return labels(data) AS Class, data")
    print(rst)