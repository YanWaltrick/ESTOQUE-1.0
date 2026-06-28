-- Executado automaticamente pelo container MySQL na primeira inicialização
-- (montado em /docker-entrypoint-initdb.d). Cria o banco de TESTE dedicado e
-- concede acesso ao usuário de aplicação. O banco de dev (estoque_db) e o
-- usuário `estoque` já são criados pelas variáveis MYSQL_* do docker-compose.

CREATE DATABASE IF NOT EXISTS estoque_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

GRANT ALL PRIVILEGES ON estoque_db.*   TO 'estoque'@'%';
GRANT ALL PRIVILEGES ON estoque_test.* TO 'estoque'@'%';
FLUSH PRIVILEGES;
