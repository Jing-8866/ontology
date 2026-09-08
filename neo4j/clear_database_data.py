#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j 数据清理脚本 - 按指定数据库删除所有非系统数据
"""

from neo4j import GraphDatabase
import logging
import sys
from typing import List, Optional, Tuple

import neo4j_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

neo4j_con = neo4j_config.neo4j_connection("local")

CONFIG = {
    "user": neo4j_con.get("username", "neo4j"),
    "password": neo4j_con.get("password", ""),
    "default_database": neo4j_con.get("default_database", ""),
    "url": neo4j_con.get("url", f"{neo4j_con['url_prefix']}://{neo4j_con['host']}:{neo4j_con['port']}")
}


class Neo4jCleaner:
    """Neo4j 数据清理器 - 支持按数据库清理"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("连接已关闭")
    
    def get_databases(self) -> List[str]:
        """获取所有非系统数据库列表"""
        with self.driver.session(database="system") as session:
            result = session.run("SHOW DATABASES")
            databases = []
            for record in result:
                name = record['name']
                # 排除系统数据库
                if name not in ['system', 'neo4j']:
                    databases.append(name)
            return databases
    
    def switch_database(self, database: str):
        """切换到指定数据库"""
        try:
            with self.driver.session(database=database) as session:
                session.run("MATCH (n) RETURN n LIMIT 1")
            logger.info(f"已切换到数据库: {database}")
            return True
        except Exception as e:
            logger.error(f"切换到数据库 {database} 失败: {e}")
            return False
    
    def get_stats(self, database: str = None) -> Tuple[int, int]:
        """获取指定数据库的统计信息"""
        db = database or "neo4j"
        try:
            with self.driver.session(database=db) as session:
                node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()['count']
                
                logger.info(f"数据库 '{db}' 当前状态:")
                logger.info(f"  节点数量: {node_count}")
                logger.info(f"  关系数量: {rel_count}")
                
                return node_count, rel_count
        except Exception as e:
            logger.error(f"获取数据库 {db} 统计信息失败: {e}")
            return 0, 0
    
    def delete_all_data_in_database(self, database: str, batch_size: int = 50000):
        """
        删除指定数据库中的所有非系统数据
        
        :param database: 数据库名称
        :param batch_size: 每批处理的行数（大数据量时使用）
        """
        logger.info(f"开始清理数据库: {database}")
        
        with self.driver.session(database=database) as session:
            # 1. 获取数据量决定策略
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
            
            if node_count > 100000:
                # 大数据量：分批删除
                logger.info(f"检测到大容量数据 ({node_count} 节点)，采用分批删除策略...")
                
                # 先删关系
                logger.info("步骤1: 分批删除关系...")
                session.run(
                    """
                    MATCH ()-[r]->()
                    CALL { WITH r DELETE r }
                    IN TRANSACTIONS OF $batch ROWS
                    """,
                    batch=batch_size
                )
                
                # 再删节点
                logger.info("步骤2: 分批删除节点...")
                session.run(
                    """
                    MATCH (n)
                    CALL { WITH n DETACH DELETE n }
                    IN TRANSACTIONS OF $batch ROWS
                    """,
                    batch=batch_size
                )
            else:
                # 小数据量：一次性删除
                logger.info(f"检测到小容量数据 ({node_count} 节点)，采用一次性删除...")
                logger.info("步骤1: 删除所有关系和节点...")
                session.run("MATCH (n) DETACH DELETE n")
            
            # 2. 删除自定义索引
            logger.info("步骤3: 删除自定义索引...")
            self._drop_indexes(session)
            
            # 3. 删除自定义约束
            logger.info("步骤4: 删除自定义约束...")
            self._drop_constraints(session)
            
            logger.info(f"数据库 '{database}' 清理完成！")
    
    def delete_all_databases(self, exclude: List[str] = None):
        """
        删除所有非系统数据库中的数据
        
        :param exclude: 排除的数据库列表
        """
        exclude = exclude or []
        databases = self.get_databases()
        
        for db in databases:
            if db in exclude:
                logger.info(f"跳过数据库: {db} (已在排除列表)")
                continue
            
            self.delete_all_data_in_database(db)
    
    def _drop_indexes(self, session):
        """删除自定义索引"""
        result = session.run("SHOW INDEXES")
        indexes_to_drop = []
        for record in result:
            # 跳过系统索引和LOOKUP索引
            if not record.get('system', False) and record.get('type') != 'LOOKUP':
                indexes_to_drop.append(record['name'])
        
        for idx_name in indexes_to_drop:
            try:
                session.run(f"DROP INDEX {idx_name} IF EXISTS")
                logger.info(f"  已删除索引: {idx_name}")
            except Exception as e:
                logger.warning(f"  删除索引 {idx_name} 失败: {e}")
    
    def _drop_constraints(self, session):
        """删除自定义约束"""
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


def quick_clean_all(exclude: List[str] = None):
    """
    快速清理所有非系统数据库，无需确认
    
    :param exclude: 排除的数据库列表，例如 ["important_db"]
    """
    cleaner = Neo4jCleaner(CONFIG["url"], CONFIG["user"], CONFIG["password"])
    
    try:
        # 获取所有非系统数据库
        databases = cleaner.get_databases()
        
        if not databases:
            logger.info("没有找到非系统数据库，只清理默认数据库 neo4j")
            databases = ["neo4j"]
        
        # 过滤排除的数据库
        exclude = exclude or []
        databases_to_clean = [db for db in databases if db not in exclude]
        
        if not databases_to_clean:
            logger.warning("所有数据库都在排除列表中，没有可清理的数据库")
            return
        
        logger.info(f"将清理以下 {len(databases_to_clean)} 个数据库: {databases_to_clean}")
        
        # 逐个清理
        for db in databases_to_clean:
            cleaner.delete_all_data_in_database(db)
        
        logger.info(f"✅ 所有数据库清理完成！共清理 {len(databases_to_clean)} 个数据库")
        
    except Exception as e:
        logger.error(f"清理失败: {e}")
        raise
    finally:
        cleaner.close()


def quick_clean_all_with_progress(exclude: List[str] = None):
    """
    带进度显示的快速清理所有数据库
    """
    cleaner = Neo4jCleaner(CONFIG["url"], CONFIG["user"], CONFIG["password"])
    
    try:
        databases = cleaner.get_databases()
        
        if not databases:
            databases = ["neo4j"]
        
        exclude = exclude or []
        databases_to_clean = [db for db in databases if db not in exclude]
        
        total = len(databases_to_clean)
        logger.info(f"开始清理 {total} 个数据库...")
        
        for i, db in enumerate(databases_to_clean, 1):
            logger.info(f"[{i}/{total}] 正在清理数据库: {db}")
            
            # 获取清理前的统计
            before = cleaner.get_stats(db)
            logger.info(f"  清理前: {before[0]} 节点, {before[1]} 关系")
            
            # 执行清理
            cleaner.delete_all_data_in_database(db)
            
            # 获取清理后的统计
            after = cleaner.get_stats(db)
            logger.info(f"  清理后: {after[0]} 节点, {after[1]} 关系")
            
            logger.info(f"[{i}/{total}] ✅ 数据库 '{db}' 清理完成")
        
        logger.info(f"🎉 全部完成！共清理 {total} 个数据库")
        
    except Exception as e:
        logger.error(f"清理过程中出错: {e}")
        raise
    finally:
        cleaner.close()

def interactive_clean():
    """交互式清理 - 选择要清理的数据库"""
    
    cleaner = Neo4jCleaner(CONFIG["url"], CONFIG["user"], CONFIG["password"])
    
    try:
        # 1. 获取可用数据库
        print("\n=== 可用的非系统数据库 ===")
        databases = cleaner.get_databases()
        
        if not databases:
            print("没有找到非系统数据库")
            print("默认数据库: neo4j")
            databases = ["neo4j"]
        else:
            for i, db in enumerate(databases, 1):
                print(f"  {i}. {db}")
        
        # 2. 选择数据库
        print("\n请选择操作:")
        print("  1. 清理指定数据库")
        print("  2. 清理所有非系统数据库")
        print("  3. 清理默认数据库 (neo4j)")
        
        choice = input("\n请输入选项 (1-3): ").strip()
        
        if choice == "1":
            # 选择具体数据库
            if databases:
                print("\n请选择要清理的数据库编号:")
                for i, db in enumerate(databases, 1):
                    stats = cleaner.get_stats(db)
                    print(f"  {i}. {db} (节点:{stats[0]}, 关系:{stats[1]})")
                
                db_choice = input("请输入编号: ").strip()
                try:
                    db_index = int(db_choice) - 1
                    if 0 <= db_index < len(databases):
                        selected_db = databases[db_index]
                    else:
                        print("无效选择，使用默认数据库")
                        selected_db = "neo4j"
                except ValueError:
                    print("无效输入，使用默认数据库")
                    selected_db = "neo4j"
            else:
                selected_db = "neo4j"
            
            # 确认
            cleaner.get_stats(selected_db)
            confirm = input(f"\n⚠️  确认清理数据库 '{selected_db}'? (输入 YES 确认): ")
            
            if confirm.upper() == "YES" :
                cleaner.delete_all_data_in_database(selected_db)
                print(f"\n✅ 数据库 '{selected_db}' 清理完成！")
            else:
                print("❌ 操作已取消")
                
        elif choice == "2":
            # 清理所有数据库
            print("\n即将清理以下数据库:")
            for db in databases:
                stats = cleaner.get_stats(db)
                print(f"  - {db} (节点:{stats[0]}, 关系:{stats[1]})")
            
            confirm = input("\n⚠️  确认清理所有非系统数据库? (输入 YES 确认): ")
            
            if confirm.upper() == "YES":
                cleaner.delete_all_databases()
                print("\n✅ 所有数据库清理完成！")
            else:
                print("❌ 操作已取消")
                
        else:
            # 清理默认数据库
            cleaner.get_stats("neo4j")
            confirm = input("\n⚠️  确认清理默认数据库 'neo4j'? (输入 YES 确认): ")
            
            if confirm.upper() == "YES":
                cleaner.delete_all_data_in_database("neo4j")
                print("\n✅ 默认数据库清理完成！")
            else:
                print("❌ 操作已取消")
    
    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        cleaner.close()


def quick_clean(database: str = "neo4j"):
    """
    快速清理 - 直接清理指定数据库，无需确认
    
    :param database: 要清理的数据库名称
    """
    cleaner = Neo4jCleaner(CONFIG["url"], CONFIG["user"], CONFIG["password"])
    
    try:
        logger.info(f"快速清理数据库: {database}")
        cleaner.delete_all_data_in_database(database)
        logger.info(f"✅ 数据库 '{database}' 清理完成！")
    except Exception as e:
        logger.error(f"清理失败: {e}")
    finally:
        cleaner.close()


def clean_multiple_databases(databases: List[str]):
    """
    清理多个指定的数据库
    
    :param databases: 要清理的数据库名称列表
    """
    cleaner = Neo4jCleaner(CONFIG["url"], CONFIG["user"], CONFIG["password"])
    
    try:
        for db in databases:
            logger.info(f"开始清理数据库: {db}")
            cleaner.delete_all_data_in_database(db)
            logger.info(f"✅ 数据库 '{db}' 清理完成！")
    except Exception as e:
        logger.error(f"清理失败: {e}")
    finally:
        cleaner.close()


def main():
    # 命令行参数支持
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--quick" or command == "-q":
            # 快速清理指定数据库
            db = sys.argv[2] if len(sys.argv) > 2 else "neo4j"
            quick_clean(db)
            
        elif command == "--all" or command == "-a":
            # 清理所有数据库
            quick_clean_all()
            
        elif command == "--all-progress" or command == "-ap":
            # 带进度清理所有数据库
            quick_clean_all_with_progress()
            
        elif command == "--list" or command == "-l":
            # 列出所有数据库
            cleaner = Neo4jCleaner(CONFIG["url"], CONFIG["user"], CONFIG["password"])
            try:
                databases = cleaner.get_databases()
                print("\n可用的非系统数据库:")
                for db in databases:
                    stats = cleaner.get_stats(db)
                    print(f"  - {db} (节点:{stats[0]}, 关系:{stats[1]})")
            finally:
                cleaner.close()
                
        elif command == "--help" or command == "-h":
            print("""
Neo4j 数据清理工具

用法:
  python clean_neo4j.py                  # 交互式清理
  python clean_neo4j.py --quick [db]     # 快速清理指定数据库
  python clean_neo4j.py --all            # 清理所有非系统数据库
  python clean_neo4j.py --list           # 列出所有数据库
  python clean_neo4j.py --help           # 显示帮助信息
            """)
        else:
            print(f"未知命令: {command}")
            print("使用 --help 查看帮助")
    else:
        # 默认交互模式
        interactive_clean()
        
if __name__ == "__main__":
    main()