from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.entity.db_models import User, UserRole, Role
from app.core.security import hash_password, verify_password, create_token
from app.core.logger import get_logger

logger = get_logger("user_service")


class UserService:
    def register(self, db: Session, username: str, email: str, password: str) -> User:
        """⽤户注册"""
        # 检查⽤户名是否已存在
        existing_user = db.query(User).filter(
            User.username == username).first()
        if existing_user:
            logger.warning(f"注册失败: 用户名已存在 - {username}")
            raise HTTPException(status_code=400, detail="用户名已存在")

        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            logger.warning(f"注册失败: 邮箱已被注册 - {email}")
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        # 创建⽤户
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"用户注册成功: {username} (id={user.id})")
        return user

    def login(self, db: Session, username: str, password: str) -> User:
        """⽤户登录"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {username}")
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not verify_password(password, user.hashed_password):
            logger.warning(f"登录失败: 密码错误 - {username}")
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not user.is_active:
            logger.warning(f"登录失败: 账户已禁用 - {username}")
            raise HTTPException(status_code=403, detail="账户已被禁用")

        # 更新最后登录时间
        user.last_login_at = datetime.now()
        db.commit()

        logger.info(f"用户登录成功: {username} (id={user.id})")
        return user

    def create_access_token_for_user(self, user: User) -> str:
        """为⽤户创建 JWT Token"""
        return create_token({"sub": str(user.id)})

    def get_user_by_id(self, db: Session, user_id: int) -> User:
        """根据 ID 获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    def get_user_roles(self, db: Session, user: User) -> list:
        """获取用户角色列表"""
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == user.id).all()
        roles = []
        for ur in user_roles:
            role = db.query(Role).get(ur.role_id)
            if role:
                roles.append(role.name)
        return roles

    def change_password(self, db: Session, user_id: int, old_password: str, new_password: str):
        """修改密码"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 验证旧密码
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("旧密码错误")

        # 新旧密码不能相同
        if old_password == new_password:
            raise ValueError("新密码不能与旧密码相同")

        # 更新密码
        user.hashed_password = hash_password(new_password)
        db.commit()

# 全局单例
user_service = UserService()
