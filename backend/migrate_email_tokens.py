from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

def col_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None

with app.app_context():
    with db.engine.connect() as conn:
        added = []
        
        # Add is_verified
        if not col_exists(conn, 'users', 'is_verified'):
            conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
            added.append('users.is_verified')
            
        # Add verification_token
        if not col_exists(conn, 'users', 'verification_token'):
            conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR(100)"))
            added.append('users.verification_token')
            
        # Add reset_token
        if not col_exists(conn, 'users', 'reset_token'):
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(100)"))
            added.append('users.reset_token')
            
        # Add otp_token
        if not col_exists(conn, 'users', 'otp_token'):
            conn.execute(text("ALTER TABLE users ADD COLUMN otp_token VARCHAR(10)"))
            added.append('users.otp_token')
            
        # Add otp_expiry
        if not col_exists(conn, 'users', 'otp_expiry'):
            conn.execute(text("ALTER TABLE users ADD COLUMN otp_expiry TIMESTAMP"))
            added.append('users.otp_expiry')
            
        # Add token_expiry
        if not col_exists(conn, 'users', 'token_expiry'):
            conn.execute(text("ALTER TABLE users ADD COLUMN token_expiry TIMESTAMP"))
            added.append('users.token_expiry')
            
        conn.commit()

    if added:
        print(f"[OK] Added columns: {', '.join(added)}")
        # Initialize is_verified to True for existing users if desired, 
        # but for this flow we might want to keep them False or set to True.
        # Let's set existing users to True so they don't get locked out.
        with db.engine.connect() as conn:
            conn.execute(text("UPDATE users SET is_verified = TRUE WHERE is_verified IS NULL OR is_verified = FALSE"))
            conn.commit()
            print("[OK] Set is_verified=True for existing users.")
    else:
        print("[OK] All email token columns already exist.")
