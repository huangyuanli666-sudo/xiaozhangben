"""初始化数据库，创建管理员账号"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from models import SessionLocal, User
from auth import hash_password

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

db = SessionLocal()
existing = db.query(User).filter(User.is_admin == True).first()
if existing:
    print(f"管理员已存在: {existing.username}")
else:
    admin = User(username=ADMIN_USER, password_hash=hash_password(ADMIN_PASS), nickname="管理员", is_admin=True)
    db.add(admin)
    db.commit()
    print(f"管理员已创建: {ADMIN_USER} / {ADMIN_PASS}")
db.close()
