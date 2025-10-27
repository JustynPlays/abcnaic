import sqlite3
import pymysql
import sys
from datetime import datetime

class SQLiteToMySQLConverter:
    def __init__(self, sqlite_path, mysql_host='localhost', mysql_user='root', mysql_password='', mysql_database='animal_bite_center'):
        self.sqlite_path = sqlite_path
        self.mysql_host = mysql_host
        self.mysql_user = mysql_user
        self.mysql_password = mysql_password
        self.mysql_database = mysql_database

        # Connect to databases
        self.sqlite_conn = sqlite3.connect(sqlite_path)
        self.sqlite_conn.row_factory = sqlite3.Row

        try:
            self.mysql_conn = pymysql.connect(
                host=mysql_host,
                user=mysql_user,
                password=mysql_password,
                database=mysql_database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("Connected to MySQL database: " + mysql_database)
        except pymysql.Error as e:
            print(f"MySQL connection failed: {e}")
            sys.exit(1)

    def get_table_schema(self, table_name):
        """Get SQLite table schema"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return columns

    def create_mysql_table(self, table_name, columns):
        """Create MySQL table with same structure"""
        mysql_cursor = self.mysql_conn.cursor()

        # Build CREATE TABLE statement
        column_defs = []
        primary_keys = []

        for col in columns:
            col_name = col[1]
            col_type = col[2]
            is_nullable = col[3] == 0  # SQLite: 0 = NOT NULL, 1 = NULL
            default_value = col[4]
            is_primary = col[5] == 1   # SQLite primary key flag

            # Convert SQLite types to MySQL types
            mysql_type = self.convert_sqlite_type_to_mysql(col_type)

            # Build column definition
            col_def = f"`{col_name}` {mysql_type}"

            if not is_nullable:
                col_def += " NOT NULL"

            if default_value is not None:
                if col_type.upper() in ['TEXT', 'VARCHAR', 'CHAR']:
                    col_def += f" DEFAULT '{default_value}'"
                else:
                    col_def += f" DEFAULT {default_value}"

            if is_primary:
                primary_keys.append(col_name)

            column_defs.append(col_def)

        # Add primary key constraint
        if primary_keys:
            column_defs.append(f"PRIMARY KEY ({','.join(f'`{pk}`' for pk in primary_keys)})")

        # Add AUTO_INCREMENT for id columns
        for col in columns:
            if col[1] == 'id' and col[5] == 1:  # Primary key id column
                # Find the column definition and modify it
                for i, col_def in enumerate(column_defs):
                    if col_def.startswith('`id`'):
                        column_defs[i] = col_def.replace('INT', 'INT AUTO_INCREMENT')
                        break

        create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n  " + ",\n  ".join(column_defs) + "\n)"

        try:
            mysql_cursor.execute(create_sql)
            self.mysql_conn.commit()
            print(f"Created MySQL table: {table_name}")
        except pymysql.Error as e:
            print(f"Failed to create table {table_name}: {e}")
            return False

        return True

    def convert_sqlite_type_to_mysql(self, sqlite_type):
        """Convert SQLite data types to MySQL data types"""
        sqlite_type = sqlite_type.upper()

        if sqlite_type == 'INTEGER':
            return 'INT'
        elif sqlite_type == 'TEXT':
            return 'TEXT'
        elif sqlite_type.startswith('VARCHAR'):
            return sqlite_type  # Keep VARCHAR length
        elif sqlite_type == 'REAL':
            return 'DECIMAL(10,2)'
        elif sqlite_type == 'BLOB':
            return 'LONGBLOB'
        elif sqlite_type == 'DATETIME' or sqlite_type == 'TIMESTAMP':
            return 'DATETIME'
        else:
            return 'TEXT'  # Default fallback

    def convert_data(self, table_name):
        """Convert data from SQLite to MySQL"""
        sqlite_cursor = self.sqlite_conn.cursor()
        mysql_cursor = self.mysql_conn.cursor()

        try:
            # Get all data from SQLite table
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()

            if not rows:
                print(f"No data found in table: {table_name}")
                return True

            # Get column names for INSERT statement
            column_names = [col[1] for col in self.get_table_schema(table_name)]
            placeholders = ','.join(['%s'] * len(column_names))
            insert_sql = f"INSERT INTO `{table_name}` ({','.join(f'`{col}`' for col in column_names)}) VALUES ({placeholders})"

            # Convert and insert data in batches
            batch_size = 100
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]

                # Convert SQLite Row objects to tuples and handle data types
                converted_batch = []
                for row in batch:
                    converted_row = []
                    for value in row:
                        if value is None:
                            converted_row.append(None)
                        elif isinstance(value, str):
                            converted_row.append(value)
                        elif isinstance(value, (int, float)):
                            converted_row.append(value)
                        elif isinstance(value, bytes):
                            converted_row.append(value)  # Keep as bytes for BLOB
                        else:
                            converted_row.append(str(value))  # Convert other types to string

                    converted_batch.append(tuple(converted_row))

                try:
                    mysql_cursor.executemany(insert_sql, converted_batch)
                    self.mysql_conn.commit()
                except pymysql.Error as e:
                    print(f"Failed to insert batch {i//batch_size + 1} for table {table_name}: {e}")
                    return False

            print(f"Converted {len(rows)} rows for table: {table_name}")
            return True

        except Exception as e:
            print(f"Error converting data for table {table_name}: {e}")
            return False

    def convert_all_tables(self):
        """Convert all tables from SQLite to MySQL"""
        sqlite_cursor = self.sqlite_conn.cursor()

        # Get all tables
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [table[0] for table in sqlite_cursor.fetchall()]

        print(f"\nStarting conversion of {len(tables)} tables...")
        print("=" * 60)

        success_count = 0
        for table_name in tables:
            print(f"\nProcessing table: {table_name}")

            # Get table schema
            columns = self.get_table_schema(table_name)

            # Create MySQL table
            if self.create_mysql_table(table_name, columns):
                # Convert data
                if self.convert_data(table_name):
                    success_count += 1
                else:
                    print(f"Data conversion failed for table: {table_name}")
            else:
                print(f"Table creation failed for table: {table_name}")

        print("\n" + "=" * 60)
        print(f"Conversion completed! {success_count}/{len(tables)} tables converted successfully")

        return success_count == len(tables)

    def close_connections(self):
        """Close database connections"""
        self.sqlite_conn.close()
        self.mysql_conn.close()
        print("Database connections closed")

def main():
    # Configuration
    SQLITE_DB_PATH = 'db/users.db'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''  # Update this if your MySQL has a password
    MYSQL_DATABASE = 'animal_bite_center'

    print("SQLite to MySQL Database Converter")
    print("=" * 60)

    # Check if SQLite database exists
    try:
        with open(SQLITE_DB_PATH, 'r'):
            pass
    except FileNotFoundError:
        print(f"ERROR: SQLite database not found: {SQLITE_DB_PATH}")
        sys.exit(1)

    # Initialize converter
    converter = SQLiteToMySQLConverter(
        SQLITE_DB_PATH,
        MYSQL_HOST,
        MYSQL_USER,
        MYSQL_PASSWORD,
        MYSQL_DATABASE
    )

    try:
        # Perform conversion
        success = converter.convert_all_tables()

        if success:
            print("\nDatabase conversion completed successfully!")
            print("You can now use your MySQL database with XAMPP")
        else:
            print("\nSome tables failed to convert. Please check the errors above.")
            print("You may need to manually fix the issues and run again")
    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error during conversion: {e}")
    finally:
        converter.close_connections()

if __name__ == "__main__":
    main()
