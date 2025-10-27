import requests

# Test accessing the registration page
try:
    response = requests.get('http://127.0.0.1:5000/register')
    print(f'Registration page status: {response.status_code}')
    print(f'Contains Register text: {"Register" in response.text}')
    print(f'Contains form: {"<form" in response.text}')
except Exception as e:
    print(f'Error accessing registration page: {e}')
