# 小账本 v0.2 — 云同步版

## 功能

| 功能 | 说明 |
|---|---|
| 注册 / 登录 | 云端账号，密码 pbkdf2 加密存储 |
| 记支出 / 记收入 | 金额、分类、备注、日期，支持编辑、删除 |
| 云同步 | 数据优先存云端（SQLite），网络不通时自动降级到本机 localStorage，恢复联网后自动上传 |
| 明细 | 按月浏览，按日分组，每日小计 |
| 统计 | 本月收支结余、支出分类占比条形图、近 7 天支出柱状图 |
| 备份 | 一键导出 JSON / 导入恢复 |
| 多设备 | 换手机登录同一账号，数据自动同步 |
| 管理后台 | 管理员登录查看所有用户和数据统计 |
| 外观 | 深色 / 浅色 / 跟随系统 |

## 架构

```
index.html   ───  前端应用（登录/注册/记账/统计）
admin.html   ───  管理后台（用户列表/数据概览）
server/
  main.py    ───  FastAPI 后端
  models.py  ───  SQLAlchemy 数据模型（SQLite）
  auth.py    ───  JWT 认证（pbkdf2 密码哈希）
  init_db.py ───  初始化数据库 + 创建管理员
  requirements.txt
```

## 快速开始

### 1. 安装依赖
```bash
cd expense-tracker/server
pip install -r requirements.txt
```

### 2. 初始化数据库（创建管理员）
```bash
python init_db.py
# → 管理员：admin / admin123
```

### 3. 启动服务
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. 使用
- **前端应用**：`http://电脑IP:8000` 或用浏览器打开 `index.html`（自动连接后端 API）
- **管理后台**：`http://电脑IP:8000/admin`
- 手机和电脑连同一 Wi-Fi，访问 `http://电脑IP:8000` 即可

### 5. 设置第一个管理员
编辑 `server/init_db.py` 修改 `ADMIN_USER` / `ADMIN_PASS`，重新运行。
也可之后在前端注册任意账号，然后手动在数据库中将其 `is_admin` 改为 1：
```bash
cd expense-tracker/server
python -c "from models import SessionLocal, User; db=SessionLocal(); u=db.query(User).filter(User.username=='你的账号').first(); u.is_admin=True; db.commit(); db.close()"
```

## APK 打包

三条路线（详见之前草稿说明，此处不变）：
- HBuilderX 云打包（推荐，无需装 SDK）
- Capacitor 本地打包（需 Node + Android Studio + JDK）
- 第三方在线打包

打包时只需将部署后的公网 URL 设为 `index.html` 中 `const API = "https://你的域名"`，再将整个 `expense-tracker/` 目录打包为 APK。

## 部署到公网（免费）

| 平台 | 说明 |
|---|---|
| [Zeabur](https://zeabur.com) | 国内节点，$5 免费额度/月，支持 Python，Git 推送即部署 |
| [Render](https://render.com) | 免费 750h/月，支持 Python，`* .onrender.com` 免费域名 |
| 自己的 VPS | 装 Python 3.12+，`pip install -r requirements.txt`，`uvicorn` 启动后配置 Nginx 反代 |

## 防闪退 / 防丢数据

- **金额以「分」存储**，杜绝浮点误差
- **云端 + 本地双写**：API 失败自动降级 localStorage，网络恢复自动同步
- **pbkdf2 密码哈希**，无第三方认证依赖，bcrypt/passlib 版本冲突风险已消除
- 后端 SQLite 单文件，零外部依赖，部署只需 Python

## 后续迭代

- 月度预算与超支提醒
- 密码锁 / 指纹锁（APK）
- 多账本
- 更丰富图表
