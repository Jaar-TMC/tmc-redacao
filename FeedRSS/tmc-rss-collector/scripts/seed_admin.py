"""
Seed script: creates the initial admin user.
Usage: python scripts/seed_admin.py
Reads ADMIN_EMAIL and ADMIN_PASSWORD from environment or local.settings.json.
"""
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_local_settings():
    """Load environment variables from local.settings.json."""
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "local.settings.json"
    )
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)
            for key, value in settings.get("Values", {}).items():
                os.environ.setdefault(key, str(value))


def main():
    load_local_settings()

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@tmc.com.br")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin_name = os.environ.get("ADMIN_NAME", "Administrador")

    if not admin_password:
        print("ERROR: Set ADMIN_PASSWORD environment variable or in local.settings.json")
        sys.exit(1)

    if len(admin_password) < 10:
        print("ERROR: Password must be at least 10 characters")
        sys.exit(1)

    from services.auth_service import hash_password
    from services.database import get_db
    from models import UserCreate

    db = get_db()

    # Check if admin already exists
    existing = db.get_user_by_email(admin_email)
    if existing:
        print(f"Admin user already exists: {admin_email}")
        sys.exit(0)

    # Create admin
    user_data = UserCreate(name=admin_name, email=admin_email, password=admin_password, role="admin")
    password_hash = hash_password(admin_password)
    user = db.create_user(user_data, password_hash)

    # Set as not new (admin doesn't need onboarding)
    db.set_user_not_new(str(user.id))

    print(f"Admin user created successfully:")
    print(f"  Email: {admin_email}")
    print(f"  Name: {admin_name}")
    print(f"  ID: {user.id}")


if __name__ == "__main__":
    main()
