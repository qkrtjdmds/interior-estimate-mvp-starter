import argparse
import getpass
import sys

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.security import normalize_email, validate_password_policy
from app.crud.admin_user import create_admin_user, get_admin_user_by_email
from app.db.session import SessionLocal


def prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise ValueError("Passwords do not match")
    validate_password_policy(password)
    return password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    args = parser.parse_args()
    email = normalize_email(args.email)
    if not email:
        print("Email is required")
        return 1

    try:
        password = prompt_password()
    except ValueError as exc:
        print(str(exc))
        return 1

    with SessionLocal() as db:
        try:
            if get_admin_user_by_email(db, email) is not None:
                print("Admin user already exists")
                return 1
            create_admin_user(db, email, password)
        except IntegrityError:
            db.rollback()
            print("Admin user already exists")
            return 1
        except SQLAlchemyError:
            db.rollback()
            print("Database operation failed")
            return 1

    print(f"Admin user created: {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
