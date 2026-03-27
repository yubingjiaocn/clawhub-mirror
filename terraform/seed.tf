resource "null_resource" "seed_admin" {
  depends_on = [aws_dynamodb_table.this]

  triggers = {
    table_name = aws_dynamodb_table.this.id
  }

  provisioner "local-exec" {
    interpreter = ["python3", "-c"]
    environment = {
      TABLE_NAME     = aws_dynamodb_table.this.id
      REGION         = var.region
      ADMIN_USERNAME = var.admin_username
      ADMIN_PASSWORD = var.admin_password
    }
    command = <<-PYEOF
import os, time, secrets, json
import boto3

table_name = os.environ["TABLE_NAME"]
region = os.environ["REGION"]
username = os.environ["ADMIN_USERNAME"]
password = os.environ["ADMIN_PASSWORD"]

ddb = boto3.resource("dynamodb", region_name=region)
table = ddb.Table(table_name)

# Check if admin already exists (idempotent)
resp = table.get_item(Key={"PK": f"USER#{username}", "SK": "PROFILE"})
if resp.get("Item"):
    print(f"Admin user '{username}' already exists. Skipping seed.")
else:
    try:
        import bcrypt
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        print("WARNING: bcrypt not available, using SHA-256 hash. Re-seed after deploying Lambda.")

    token = secrets.token_urlsafe(32)
    now = int(time.time() * 1000)

    table.put_item(Item={
        "PK": f"USER#{username}",
        "SK": "PROFILE",
        "username": username,
        "hashedPassword": hashed,
        "role": "admin",
        "apiToken": token,
        "isActive": True,
        "createdAt": now,
        "GSI3PK": f"TOKEN#{token}",
        "GSI3SK": "TOKEN",
    })
    print(f"Admin user '{username}' created successfully.")
    print(f"Password: {password}")
    print(f"API Token: {token}")
    print("IMPORTANT: Change the default password after first login.")
PYEOF
  }
}
