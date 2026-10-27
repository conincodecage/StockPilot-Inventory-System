-- Run this script as SYSTEM (or another DBA account) in the target pluggable database.
-- Change the password before using anything beyond a local classroom demo.
CREATE USER INVENTORY_APP IDENTIFIED BY "ChangeMe_123"
  DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE,
      CREATE TRIGGER, CREATE VIEW TO INVENTORY_APP;
ALTER USER INVENTORY_APP QUOTA UNLIMITED ON USERS;
-- Then connect as INVENTORY_APP before running 01_schema.sql through 04_seed_demo.sql.
