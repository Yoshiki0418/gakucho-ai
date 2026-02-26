import os
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("DB_URL not set in .env")
        return

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            # Drop the table
            print("Dropping table ohsawa_context...")
            cur.execute("DROP TABLE IF EXISTS ohsawa_context;")
            
            # Read schema.sql and execute
            schema_path = os.path.join(os.path.dirname(__file__), "app", "rag", "schema.sql")
            print(f"Applying schema from {schema_path}...")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
                
            cur.execute(schema_sql)
            print("Schema applied successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
