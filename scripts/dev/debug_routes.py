from app import create_app

app = create_app()
print('\n-- Registered URL rules --')
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    print(rule.rule, list(rule.methods))

# Try a test client POST
client = app.test_client()
resp = client.post('/check-email', json={'email':'nonexistent@example.com'})
print('\nPOST /check-email status:', resp.status_code)
print('data:', resp.get_data(as_text=True))
