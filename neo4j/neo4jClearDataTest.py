#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j 数据清理脚本 - 删除所有非系统数据
"""

from neo4j import GraphDatabase
import logging

import neo4j_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

class Neo4jCleaner:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("连接已关闭")
    
    def delete_all_data(self):
        """删除所有非系统数据（节点、关系、索引、约束）"""
        with self.driver.session() as session:
            # 1. 删除所有关系和节点（先删关系再删节点）
            logger.info("步骤1: 删除所有关系和节点...")
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("所有关系和节点已删除")
            
            # 2. 删除所有自定义索引（保留系统索引）
            logger.info("步骤2: 删除自定义索引...")
            result = session.run("SHOW INDEXES")
            indexes_to_drop = []
            for record in result:
                # 跳过系统索引（通常名称以 system_ 开头或属于系统数据库）
                if not record.get('system', False) and record.get('type') != 'LOOKUP':
                    indexes_to_drop.append(record['name'])
            
            for idx_name in indexes_to_drop:
                try:
                    session.run(f"DROP INDEX {idx_name} IF EXISTS")
                    logger.info(f"  已删除索引: {idx_name}")
                except Exception as e:
                    logger.warning(f"  删除索引 {idx_name} 失败: {e}")
            
            # 3. 删除所有自定义约束（保留系统约束）
            logger.info("步骤3: 删除自定义约束...")
            result = session.run("SHOW CONSTRAINTS")
            constraints_to_drop = []
            for record in result:
                if not record.get('system', False):
                    constraints_to_drop.append(record['name'])
            
            for constraint_name in constraints_to_drop:
                try:
                    session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                    logger.info(f"  已删除约束: {constraint_name}")
                except Exception as e:
                    logger.warning(f"  删除约束 {constraint_name} 失败: {e}")
            
            logger.info("数据清理完成！")
    
    def get_stats(self):
        """获取当前数据库统计信息"""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()['count']
            
            logger.info(f"当前数据库状态:")
            logger.info(f"  节点数量: {node_count}")
            logger.info(f"  关系数量: {rel_count}")
            
            return node_count, rel_count


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j 一键清理脚本 - 直接删除所有非系统数据（无需确认）
"""

def clean_neo4j(uri, user, password):
    """一键清理所有非系统数据"""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # 1. 删除所有节点和关系
            logger.info("正在删除所有节点和关系...")
            summary = session.run("MATCH (n) DETACH DELETE n").consume()
            deleted_nodes = summary.counters.nodes_deleted
            deleted_rels = summary.counters.relationships_deleted
            logger.info(f"已删除 {deleted_nodes} 个节点, {deleted_rels} 个关系")
            
            # 2. 删除所有自定义索引
            logger.info("正在删除自定义索引...")
            result = session.run("SHOW INDEXES")
            for record in result:
                if not record.get('system', False):
                    index_name = record['name']
                    try:
                        session.run(f"DROP INDEX {index_name} IF EXISTS")
                        logger.info(f"  已删除索引: {index_name}")
                    except Exception as e:
                        logger.warning(f"  删除索引 {index_name} 失败: {e}")
            
            # 3. 删除所有自定义约束
            logger.info("正在删除自定义约束...")
            result = session.run("SHOW CONSTRAINTS")
            for record in result:
                if not record.get('system', False):
                    constraint_name = record['name']
                    try:
                        session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                        logger.info(f"  已删除约束: {constraint_name}")
                    except Exception as e:
                        logger.warning(f"  删除约束 {constraint_name} 失败: {e}")
            
            logger.info("✅ 数据清理完成！")
            
    except Exception as e:
        logger.error(f"清理失败: {e}")
    finally:
        driver.close()


def clear_by_confirm():
    # 连接配置
    URI = CONFIG["url"]
    USER = CONFIG["user"]
    PASSWORD = CONFIG["password"]
    
    cleaner = Neo4jCleaner(URI, USER, PASSWORD)
    
    try:
        # 1. 先显示当前数据量
        print("\n=== 清理前数据统计 ===")
        cleaner.get_stats()
        
        # 2. 确认操作
        print("\n⚠️  警告: 即将删除所有非系统数据！")
        confirm = input("确认执行清理？(输入 YES 确认): ")
        
        if confirm.upper() == "YES":
            print("\n=== 开始清理数据 ===")
            cleaner.delete_all_data()
            
            # 3. 清理后验证
            print("\n=== 清理后数据统计 ===")
            cleaner.get_stats()
            
            print("\n✅ 数据清理成功完成！")
        else:
            print("❌ 操作已取消")
            
    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        cleaner.close()


if __name__ == "__main__":
    clear_by_confirm() # 需输入确认再删除
    # clean_neo4j(CONFIG["url"], CONFIG["user"], CONFIG["password"]) # 直接删除

    