# Migrations

schema.sql 是当前 schema 的权威源（幂等，CREATE TABLE IF NOT EXISTS）。

未来 schema 变更时，在此目录新增 `NNN_description.sql` 迁移脚本，由 `scripts/init_db.py` 按序执行。
