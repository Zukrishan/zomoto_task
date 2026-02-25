#!/bin/bash
# Ensure MySQL/MariaDB is installed and running

# Check if mysqld is available
if ! command -v mysqld &> /dev/null; then
    echo "MariaDB not found, installing..."
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq mariadb-server > /dev/null 2>&1
    echo "MariaDB installed."
fi

# Ensure socket directory exists
mkdir -p /run/mysqld
chown mysql:mysql /run/mysqld

# Check if MySQL is running
if ! mysqladmin ping --silent 2>/dev/null; then
    echo "Starting MariaDB..."
    mysqld_safe &
    # Wait for MySQL to be ready (max 15 seconds)
    for i in $(seq 1 15); do
        if mysqladmin ping --silent 2>/dev/null; then
            echo "MariaDB started successfully."
            break
        fi
        sleep 1
    done
fi

# Ensure database exists
mysql -u root -e "CREATE DATABASE IF NOT EXISTS zomoto_tasks;" 2>/dev/null
echo "MySQL ready."
