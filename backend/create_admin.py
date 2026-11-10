import getpass
import re
import sqlite3
import sys

from app.auth import connect_database, create_user
from main import DATABASE_PATH, initialize_database


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main() -> int:
    if len(sys.argv) != 2 or not EMAIL_PATTERN.fullmatch(sys.argv[1]):
        print("Usage: python create_admin.py admin@example.com", file=sys.stderr)
        return 2

    initialize_database()
    with connect_database(DATABASE_PATH) as connection:
        if connection.execute(
            "SELECT 1 FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone():
            print("An administrator already exists.", file=sys.stderr)
            return 1

    password = getpass.getpass("New administrator password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    try:
        user = create_user(DATABASE_PATH, sys.argv[1], password, role="admin")
    except sqlite3.IntegrityError:
        print("An account with that email already exists.", file=sys.stderr)
        return 1
    print(f"Administrator created: {user['email']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
