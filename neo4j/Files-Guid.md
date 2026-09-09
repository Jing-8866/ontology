
## Neo4j数据库操作工具类

| No. | filename | description | remark |
| --- | --- | --- | --- |
| 1 | `neo4j_config.py` | Get Configuration from `config/config-xx.yml` file and return as a dictionary. | main file of configuration is `config/config.yml`,mapping environments config |
| 2 | `clear_database_data.py` | Clear datas in the Neo4j database by condition. | - |
| 3 | `cypher_system_util.py` | Operation on Neo4j database using Cypher query AS system manager. | need run in `system` database |
| 4 | `cypher_util.py` | Operation on Neo4j database using Cypher query AS normal query. | normally run in non-system database(like `neo4j` database) |

