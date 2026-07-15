"""
数据库种子数据初始化。

运行方式：
    python -m app.database.seed

或在 main.py 的 lifespan 中取消注释 init_seed() 调用。
"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import get_session_local
from app.entity.db_models import Permission, Role, RolePermission, User, UserRole


# ── 角色定义 ──────────────────────────────────────────────

ROLES = [
    {
        "name": "admin",
        "display_name": "管理员",
        "description": "系统管理员，拥有全部权限",
        "is_system": True,
    },
    {
        "name": "user",
        "display_name": "普通用户",
        "description": "日常使用者",
        "is_system": True,
    },
]

# ── 权限定义 ──────────────────────────────────────────────

PERMISSIONS = [
    # 知识库
    {"code": "knowledge:upload", "name": "上传知识库", "module": "knowledge"},
    {"code": "knowledge:search", "name": "检索知识库", "module": "knowledge"},
    {"code": "knowledge:delete", "name": "删除知识库", "module": "knowledge"},
    # 摄像头
    {"code": "camera:capture", "name": "拍照上传", "module": "camera"},
    {"code": "camera:delete", "name": "删除照片", "module": "camera"},
    # 看板
    {"code": "dashboard:view", "name": "查看看板", "module": "dashboard"},
    # 检测
    {"code": "detection:run", "name": "执行检测", "module": "detection"},
    {"code": "detection:view", "name": "查看检测结果", "module": "detection"},
    # 训练
    {"code": "training:run", "name": "执行训练", "module": "training"},
    {"code": "training:view", "name": "查看训练结果", "module": "training"},
    # 用户管理
    {"code": "user:manage", "name": "管理用户", "module": "user"},
]

# ── 角色-权限分配 ────────────────────────────────────────

ROLE_PERMISSIONS = {
    "admin": [  # 管理员：全部权限
        "knowledge:upload", "knowledge:search", "knowledge:delete",
        "camera:capture", "camera:delete",
        "dashboard:view",
        "detection:run", "detection:view",
        "training:run", "training:view",
        "user:manage",
    ],
    "user": [   # 普通用户：基本使用权限
        "knowledge:upload", "knowledge:search",
        "camera:capture",
        "dashboard:view",
        "detection:run", "detection:view",
    ],
}

# ── 默认管理员 ────────────────────────────────────────────

ADMIN_USER = {
    "username": "admin",
    "email": "admin@nutrimind.com",
    "password": "admin123",
    "is_superuser": True,
    "is_active": True,
}


def seed_roles(db: Session) -> dict[str, Role]:
    """创建默认角色，返回 {name: Role} 映射。"""
    role_map = {}
    for data in ROLES:
        existing = db.query(Role).filter(Role.name == data["name"]).first()
        if existing:
            role_map[data["name"]] = existing
            continue
        role = Role(**data)
        db.add(role)
        db.flush()
        role_map[data["name"]] = role
    return role_map


def seed_permissions(db: Session) -> dict[str, Permission]:
    """创建默认权限，返回 {code: Permission} 映射。"""
    perm_map = {}
    for data in PERMISSIONS:
        existing = db.query(Permission).filter(
            Permission.code == data["code"]).first()
        if existing:
            perm_map[data["code"]] = existing
            continue
        perm = Permission(**data)
        db.add(perm)
        db.flush()
        perm_map[data["code"]] = perm
    return perm_map


def seed_role_permissions(db: Session, roles: dict, perms: dict):
    """为角色分配权限。"""
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if not role:
            continue
        for code in perm_codes:
            perm = perms.get(code)
            if not perm:
                continue
            existing = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id,
            ).first()
            if existing:
                continue
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))


def seed_admin(db: Session, roles: dict):
    """创建默认管理员并分配 admin 角色。"""
    existing = db.query(User).filter(
        User.username == ADMIN_USER["username"]).first()
    if existing:
        user = existing
    else:
        user = User(
            username=ADMIN_USER["username"],
            email=ADMIN_USER["email"],
            hashed_password=hash_password(ADMIN_USER["password"]),
            is_superuser=ADMIN_USER["is_superuser"],
            is_active=ADMIN_USER["is_active"],
        )
        db.add(user)
        db.flush()

    # 分配 admin 角色
    admin_role = roles.get("admin")
    if admin_role:
        existing_ur = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == admin_role.id,
        ).first()
        if not existing_ur:
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))


def init_seed():
    """执行全部种子数据初始化。"""
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        roles = seed_roles(db)
        perms = seed_permissions(db)
        seed_role_permissions(db, roles, perms)
        seed_admin(db, roles)
        db.commit()
        print("✅ 种子数据初始化完成")
        print(f"   角色: {list(roles.keys())}")
        print(f"   权限: {len(perms)} 个")
        print(f"   管理员: admin@nutrimind.com")
    except Exception as e:
        db.rollback()
        print(f"❌ 种子数据初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_seed()