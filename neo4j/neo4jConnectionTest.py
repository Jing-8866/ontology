#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j 连接测试脚本
适用于 Neo4j Community 5.26.0
"""

from neo4j import GraphDatabase
import logging

import neo4j_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

neo4j_con = neo4j_config.neo4j_connection("local")

CONFIG = {
    "url_prefix": neo4j_con.get("url_prefix", "bolt"),
    "host": neo4j_con.get("host", "127.0.0.1"),
    "port": int(neo4j_con.get("port", 7687)),
    "user": neo4j_con.get("username", "neo4j"),
    "password": neo4j_con.get("password", ""),
    "default_database": neo4j_con.get("default_database", ""),
    "url": neo4j_con.get("url", f"{neo4j_con['url_prefix']}://{neo4j_con['host']}:{neo4j_con['port']}")
}


class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"成功创建到 {uri} 的连接驱动")
        except Exception as e:
            logger.error(f"创建连接驱动失败: {e}")
    
    def close(self):
        """关闭连接"""
        if self.driver is not None:
            self.driver.close()
            logger.info("连接已关闭")
    
    def test_connection(self):
        """测试连接是否正常"""
        with self.driver.session() as session:
            result = session.run("RETURN 'Neo4j连接成功!' AS message")
            record = result.single()
            logger.info(record["message"])
            return record["message"]
    
    def check_version(self):
        """检查Neo4j版本"""
        with self.driver.session() as session:
            result = session.run("CALL dbms.components() YIELD name, versions, edition")
            record = result.single()
            version_info = f"数据库: {record['name']}, 版本: {record['versions'][0]}, 版本类型: {record['edition']}"
            logger.info(version_info)
            return version_info
    
    def create_sample_data(self):
        """创建示例数据"""
        with self.driver.session() as session:
            # 创建一些示例节点和关系
            session.run("""
                MERGE (a:Person {name: '张三', age: 30})
                MERGE (b:Person {name: '李四', age: 25})
                MERGE (c:City {name: '北京'})
                MERGE (d:City {name: '上海'})
                MERGE (a)-[:LIVES_IN]->(c)
                MERGE (b)-[:LIVES_IN]->(d)
                MERGE (a)-[:KNOWS {since: 2020}]->(b)
            """)
            logger.info("示例数据创建成功")
    
    def query_sample_data(self):
        """查询示例数据"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)-[r]->(n)
                RETURN p.name AS person, type(r) AS relationship, 
                       CASE WHEN n:Person THEN n.name ELSE n.name END AS target,
                       labels(n) AS target_type
            """)
            
            print("\n=== 示例数据查询结果 ===")
            for record in result:
                print(f"{record['person']} -[{record['relationship']}]-> {record['target']} ({record['target_type']})")

    def query(self, query_str) -> list[dict] | None:
        """执行查询并返回结果"""
        with self.driver.session() as session:
            result = session.run(query_str)
            
        return result


def query_neo4j(**kwargs):
    URI = CONFIG["url"]
    USER = CONFIG["user"]
    PASSWORD = CONFIG["password"]
    
    # 创建连接实例
    conn = Neo4jConnection(URI, USER, PASSWORD)

    
    try:
        query_str = kwargs.get("query_str")

        conn.query(query_str)

    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        # 关闭连接
        conn.close()

def test_con():
    # Neo4j 连接配置
    # 默认地址：bolt://localhost:7687
    # 默认用户名：neo4j
    # 密码：请替换为你自己的密码
    URI = CONFIG["url"]
    USER = CONFIG["user"]
    PASSWORD = CONFIG["password"]
    
    # 创建连接实例
    conn = Neo4jConnection(URI, USER, PASSWORD)
    
    try:
        # 1. 测试连接
        print("\n=== 测试连接 ===")
        conn.test_connection()
        
        # 2. 查看版本
        print("\n=== 查看版本 ===")
        conn.check_version()
        
        # # 3. 创建示例数据
        # print("\n=== 创建示例数据 ===")
        # conn.create_sample_data()
        
        # # 4. 查询示例数据
        # conn.query_sample_data()
        
    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        # 关闭连接
        conn.close()


if __name__ == "__main__":
    # test_con()
    query_neo4j()