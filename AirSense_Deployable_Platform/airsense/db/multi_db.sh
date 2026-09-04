#!/bin/bash
# Creates additional databases (mlflow, airflow) alongside the main airsense DB
set -e
function create_db() {
    local db=$1
    echo "Creating database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE $db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
        GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL
}
create_db mlflow
create_db airflow
echo "All databases created."
