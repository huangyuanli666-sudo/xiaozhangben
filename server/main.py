"""小账本 - 后端服务"""
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional

from models import get_db, User, Bill
from auth import hash_password, verify_password, create_token, get_current_user, admin_required

app = FastAPI(title="小账本 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- 请求/响应模型 ----------
class RegisterBody(BaseModel):
    username: str = Field(min_length=2, max_length=20)
    password: str = Field(min_length=4, max_length=32)
    nickname: str = Field(default="", max_length=16)

class LoginBody(BaseModel):
    username: str
    password: str

class BillBody(BaseModel):
    type: str = Field(pattern=r"^(expense|income)$")
    amount: int = Field(gt=0, description="金额，单位：分")
    category: str = Field(min_length=1, max_length=20)
    note: str = Field(default="", max_length=60)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

class BillUpdate(BaseModel):
    type: Optional[str] = Field(None, pattern=r"^(expense|income)$")
    amount: Optional[int] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=20)
    note: Optional[str] = Field(None, max_length=60)
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

class SyncItem(BaseModel):
    id: Optional[str] = None          # 本地 ID（用于去重）
    type: str
    amount: int
    category: str
    note: str = ""
    date: str
    createdAt: Optional[int] = None

class SyncBody(BaseModel):
    items: list[SyncItem]

# ---------- 通用工具 ----------
def make_bill_out(b: Bill) -> dict:
    return {
        "id": b.id,
        "type": b.type,
        "amount": b.amount,
        "category": b.category,
        "note": b.note,
        "date": b.date,
        "createdAt": b.created_at.isoformat() if b.created_at else None
    }

# ========== 用户 API ==========
@app.post("/api/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已被注册")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username, "nickname": user.nickname, "isAdmin": user.is_admin}}

@app.post("/api/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username, "nickname": user.nickname, "isAdmin": user.is_admin}}

@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "nickname": user.nickname, "isAdmin": user.is_admin}

# ========== 账单 API ==========
@app.get("/api/bills")
def list_bills(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = db.query(Bill).filter(Bill.user_id == user.id)
    if month:
        q = q.filter(Bill.date.like(f"{month}%"))
    bills = q.order_by(Bill.date.desc(), Bill.created_at.desc()).all()
    return [make_bill_out(b) for b in bills]

@app.post("/api/bills")
def create_bill(body: BillBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = Bill(user_id=user.id, type=body.type, amount=body.amount, category=body.category, note=body.note, date=body.date)
    db.add(b)
    db.commit()
    db.refresh(b)
    return make_bill_out(b)

@app.put("/api/bills/{bid}")
def update_bill(bid: int, body: BillUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Bill).filter(Bill.id == bid, Bill.user_id == user.id).first()
    if not b:
        raise HTTPException(404, "账单不存在")
    for k in ("type", "amount", "category", "note", "date"):
        v = getattr(body, k)
        if v is not None:
            setattr(b, k, v)
    db.commit()
    return make_bill_out(b)

@app.delete("/api/bills/{bid}")
def delete_bill(bid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Bill).filter(Bill.id == bid, Bill.user_id == user.id).first()
    if not b:
        raise HTTPException(404, "账单不存在")
    db.delete(b)
    db.commit()
    return {"ok": True}

# ---------- 同步（上传本地数据 + 拉取云端数据） ----------
@app.post("/api/sync")
def sync(body: SyncBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 去重：按 date + type + amount + category + note 判断是否已存在
    existing = db.query(Bill).filter(Bill.user_id == user.id).all()
    existing_set = set()
    for b in existing:
        existing_set.add((b.date, b.type, b.amount, b.category, b.note))

    imported = 0
    for it in body.items:
        key = (it.date, it.type, it.amount, it.category, it.note)
        if key not in existing_set:
            b = Bill(user_id=user.id, type=it.type, amount=it.amount, category=it.category, note=it.note, date=it.date)
            db.add(b)
            existing_set.add(key)
            imported += 1
    db.commit()

    # 返回云端全部数据
    all_bills = db.query(Bill).filter(Bill.user_id == user.id).order_by(Bill.date, Bill.created_at).all()
    return {"imported": imported, "bills": [make_bill_out(b) for b in all_bills]}

# ========== 管理后台 API ==========
@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(admin_required)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [{"id": u.id, "username": u.username, "nickname": u.nickname, "isAdmin": u.is_admin, "createdAt": u.created_at.isoformat() if u.created_at else None} for u in users]

@app.get("/api/admin/summary")
def admin_summary(db: Session = Depends(get_db), _: User = Depends(admin_required)):
    total_users = db.query(func.count(User.id)).scalar()
    total_bills = db.query(func.count(Bill.id)).scalar()
    total_exp = db.query(func.coalesce(func.sum(Bill.amount), 0)).filter(Bill.type == "expense").scalar()
    total_inc = db.query(func.coalesce(func.sum(Bill.amount), 0)).filter(Bill.type == "income").scalar()
    return {"totalUsers": total_users, "totalBills": total_bills, "totalExpense": total_exp, "totalIncome": total_inc}

@app.get("/api/admin/bills/{user_id}")
def admin_user_bills(user_id: int, db: Session = Depends(get_db), _: User = Depends(admin_required)):
    bills = db.query(Bill).filter(Bill.user_id == user_id).order_by(Bill.date.desc(), Bill.created_at.desc()).all()
    return [make_bill_out(b) for b in bills]

# ========== 前端静态文件（单页应用 + 管理后台） ==========
@app.get("/admin")
@app.get("/admin.html")
def admin_page():
    return FileResponse("../admin.html")

@app.get("/")
@app.get("/index.html")
def index_page():
    return FileResponse("../index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
