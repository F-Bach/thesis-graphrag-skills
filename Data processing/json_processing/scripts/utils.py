import secrets

# Generate a 16+ character secure password
password = secrets.token_urlsafe(32)
print(password)