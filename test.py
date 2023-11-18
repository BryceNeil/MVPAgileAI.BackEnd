import databases
import asyncio

async def test_database_connection():
    try:
        db = databases.Database(url="postgres://postgres:#gile4444@aa.cect20az9tah.us-east-1.rds.amazonaws.com:5432/aa")
        await db.connect()
        print("Connection to the AWS RDS database successful with databases library!")
    except Exception as e:
        print(f"Failed to connect to the AWS RDS database with databases library: {e}")
    finally:
        await db.disconnect()

asyncio.run(test_database_connection())

import psycopg2

def test_database_connection():
    try:
        connection = psycopg2.connect(
            dbname="aa",
            user="postgres",
            password="#gile4444",
            host="aa.cect20az9tah.us-east-1.rds.amazonaws.com",
            port="5432"
        )
        print("Connection to the AWS RDS database successful with psycopg2!")
        connection.close()  # Close the connection when done
    except psycopg2.Error as e:
        print(f"Failed to connect to the database with psycopg2: {e}")

test_database_connection()

async def test_database_connection():
    try:
        db = databases.Database(url="postgres://postgres:d-D12afG1gcgaFFF5dfE2GeGfCgabgC*@monorail.proxy.rlwy.net:11514/aa")
        await db.connect()
        print("Connection to the Railway database successful with databases library!")
    except Exception as e:
        print(f"Failed to connect to the Railway database with databases library: {e}")
    finally:
        await db.disconnect()

asyncio.run(test_database_connection())