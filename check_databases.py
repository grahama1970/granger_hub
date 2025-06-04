from arango import ArangoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = ArangoClient(hosts='http://localhost:8529')
sys_db = client.db('_system', username='root', password='openSesame')

print("Available databases:")
for db_name in sys_db.databases():
    print(f"  - {db_name}")
    
# Check for granger_test database
if 'granger_test' in sys_db.databases():
    print("\n✅ granger_test database exists")
    db = client.db('granger_test', username='root', password='openSesame')
    print("Collections:", [c['name'] for c in db.collections() if not c['name'].startswith('_')])
else:
    print("\n⚠️  granger_test database does not exist, creating it...")
    sys_db.create_database('granger_test')
    print("✅ Created granger_test database")
