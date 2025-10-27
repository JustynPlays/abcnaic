from app import create_app
import json

app = create_app()
client = app.test_client()

for email in ["nonexistent@example.com", "test@example.com"]:
    resp = client.post('/check-email', json={'email': email})
    print(email, resp.status_code, resp.get_data(as_text=True))
