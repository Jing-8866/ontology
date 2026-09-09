

## 1、URL  
### Web Url
```
http://localhost:7474/
```

### Connection to Neo4j Url
```
bolt://localhost:7687
```

### 初始账号密码(首次登录需要改密码)：  
```
neo4j/neo4j
```

## 2、服务启停  
```
neo4j.bat windows-service install   # 5.x 用这条（4.x 是 install-service）
neo4j.bat start
neo4j.bat status
neo4j.bat stop
```

### 临时会话使用  
在neo4j的安装目录bin/下创建一个【start-neo4j.cmd】文件
- 假设不用系统环境变量中配置的java版本
```
@ECHO OFF
SET "JAVA_HOME=D:\Software\Java\jdk-17.0.20+8"
SET "NEO4J_JAVA_HOME=D:\Software\Java\jdk-17.0.20+8"
SET "NEO4J_HOME=D:\Software\neo4j-community-5.26.0"
cd /d %NEO4J_HOME%\bin
call neo4j.bat console
PAUSE
```


## 加载import目录数据

操作流程
```
// 1. 创建约束
CREATE CONSTRAINT n10s_unique_uri FOR (r:Resource) REQUIRE r.uri IS UNIQUE;

// 2. 初始化图配置
CALL n10s.graphconfig.init({ handleVocabUris: 'SHORTEN' });

// 3. 导入本体
// Windows 使用“绝对路径”导入
CALL n10s.onto.import.fetch(
  "file:///ontology.owl",
  "RDF/XML"
);

// 4. 验证导入结果
MATCH (c:Class) RETURN c.uri LIMIT 20;
```

> Windows 使用“绝对路径”导入，斜杠用正斜杠