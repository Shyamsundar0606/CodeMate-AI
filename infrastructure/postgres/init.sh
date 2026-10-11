#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$CODEMATE_DB_PASSWORD" -v test_password="$CODEMATE_TEST_PASSWORD" <<'SQL'
CREATE ROLE codemate_user LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
ALTER DATABASE codemate_db OWNER TO codemate_user;
CREATE ROLE codemate_test_user LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'test_password';
CREATE DATABASE codemate_test_db OWNER codemate_test_user;
REVOKE CONNECT ON DATABASE codemate_db FROM PUBLIC;
GRANT CONNECT ON DATABASE codemate_db TO codemate_user;
REVOKE CONNECT ON DATABASE codemate_test_db FROM PUBLIC;
GRANT CONNECT ON DATABASE codemate_test_db TO codemate_test_user;
SQL
