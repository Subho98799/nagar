from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('ROOT:')
print(client.get('/').json())

print('\nHEALTH:')
print(client.get('/health').json())

print('\nDB HEALTH:')
try:
    resp = client.get('/health/db')
    print(resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)
except Exception as e:
    print('DB call raised exception:', e)
