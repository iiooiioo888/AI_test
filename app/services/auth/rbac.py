"""
RBAC (Role-Based Access Control) 權限控制服務
企業級字段級權限管理
"""
from enum import Enum
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


class Permission(str, Enum):
    """權限定義"""
    # 場景權限
    SCENE_CREATE = "scene:create"
    SCENE_READ = "scene:read"
    SCENE_UPDATE = "scene:update"
    SCENE_DELETE = "scene:delete"
    SCENE_LOCK = "scene:lock"
    SCENE_UNLOCK = "scene:unlock"
    SCENE_TRANSITION = "scene:transition"
    
    # 項目權限
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_MEMBERS = "project:manage_members"
    
    # 角色權限
    CHARACTER_CREATE = "character:create"
    CHARACTER_UPDATE = "character:update"
    CHARACTER_DELETE = "character:delete"
    
    # 提示詞權限
    PROMPT_CREATE = "prompt:create"
    PROMPT_UPDATE = "prompt:update"
    PROMPT_DELETE = "prompt:delete"
    
    # 生成權限
    GENERATION_SUBMIT = "generation:submit"
    GENERATION_CANCEL = "generation:cancel"
    GENERATION_VIEW = "generation:view"
    
    # 管理權限
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_AUDIT = "admin:audit"


class Role(str, Enum):
    """角色定義"""
    VIEWER = "viewer"           # 只讀
    EDITOR = "editor"           # 編輯
    DIRECTOR = "director"       # 導演 (審核、鎖定)
    ADMIN = "admin"             # 管理員
    SUPER_ADMIN = "super_admin" # 超級管理員


@dataclass
class RoleDefinition:
    """角色定義"""
    name: Role
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    inherited_roles: List[Role] = field(default_factory=list)
    
    def get_all_permissions(self) -> Set[Permission]:
        """獲取所有權限 (包括繼承)"""
        all_perms = set(self.permissions)
        for inherited_role in self.inherited_roles:
            role_def = ROLE_DEFINITIONS.get(inherited_role)
            if role_def:
                all_perms.update(role_def.get_all_permissions())
        return all_perms


# 角色權限定義
ROLE_DEFINITIONS: Dict[Role, RoleDefinition] = {
    Role.VIEWER: RoleDefinition(
        name=Role.VIEWER,
        description="只讀訪問",
        permissions={
            Permission.SCENE_READ,
            Permission.PROJECT_READ,
            Permission.GENERATION_VIEW,
        },
    ),
    Role.EDITOR: RoleDefinition(
        name=Role.EDITOR,
        description="編輯權限",
        permissions={
            Permission.SCENE_CREATE,
            Permission.SCENE_UPDATE,
            Permission.SCENE_DELETE,
            Permission.CHARACTER_CREATE,
            Permission.CHARACTER_UPDATE,
            Permission.PROMPT_CREATE,
            Permission.PROMPT_UPDATE,
            Permission.GENERATION_SUBMIT,
        },
        inherited_roles=[Role.VIEWER],
    ),
    Role.DIRECTOR: RoleDefinition(
        name=Role.DIRECTOR,
        description="導演權限 (審核、鎖定)",
        permissions={
            Permission.SCENE_LOCK,
            Permission.SCENE_UNLOCK,
            Permission.SCENE_TRANSITION,
            Permission.PROJECT_MANAGE_MEMBERS,
            Permission.GENERATION_CANCEL,
        },
        inherited_roles=[Role.EDITOR],
    ),
    Role.ADMIN: RoleDefinition(
        name=Role.ADMIN,
        description="管理員",
        permissions={
            Permission.PROJECT_CREATE,
            Permission.PROJECT_DELETE,
            Permission.CHARACTER_DELETE,
            Permission.PROMPT_DELETE,
            Permission.ADMIN_USERS,
            Permission.ADMIN_AUDIT,
        },
        inherited_roles=[Role.DIRECTOR],
    ),
    Role.SUPER_ADMIN: RoleDefinition(
        name=Role.SUPER_ADMIN,
        description="超級管理員",
        permissions={
            Permission.ADMIN_SETTINGS,
            Permission.ADMIN_USERS,
            Permission.ADMIN_AUDIT,
        },
        inherited_roles=[Role.ADMIN],
    ),
}


@dataclass
class UserContext:
    """用戶上下文"""
    user_id: str
    email: str
    username: str
    roles: List[Role] = field(default_factory=list)
    department: Optional[str] = None
    is_active: bool = True
    
    def get_all_permissions(self) -> Set[Permission]:
        """獲取用戶所有權限"""
        all_perms = set()
        for role in self.roles:
            role_def = ROLE_DEFINITIONS.get(role)
            if role_def:
                all_perms.update(role_def.get_all_permissions())
        return all_perms
    
    def has_permission(self, permission: Permission) -> bool:
        """檢查是否有指定權限"""
        return permission in self.get_all_permissions()
    
    def has_role(self, role: Role) -> bool:
        """檢查是否有指定角色"""
        return role in self.roles
    
    def has_any_role(self, roles: List[Role]) -> bool:
        """檢查是否有任一指定角色"""
        return any(role in self.roles for role in roles)


@dataclass
class ResourcePermission:
    """資源級權限"""
    resource_type: str  # 'scene', 'project', 'character'
    resource_id: str
    user_id: str
    permissions: Set[Permission] = field(default_factory=set)
    granted_by: Optional[str] = None
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class RBACService:
    """
    RBAC 權限服務
    
    功能：
    1. 角色管理
    2. 權限檢查
    3. 資源級權限
    4. 字段級權限
    
    設計理由：
    - 企業級應用需要精細的權限控制
    - 支持角色繼承
    - 支持臨時權限
    
    潛在風險：
    - 權限緩存一致性
    - 性能開銷 (需要緩存)
    """
    
    def __init__(self):
        # 用戶上下文緩存
        self.user_cache: Dict[str, UserContext] = {}
        
        # 資源級權限
        self.resource_permissions: Dict[str, Dict[str, ResourcePermission]] = {}
        
        # 字段級權限配置
        self.field_permissions: Dict[str, Dict[str, Set[Permission]]] = {
            'scene': {
                'title': {Permission.SCENE_READ},
                'description': {Permission.SCENE_READ},
                'narrative_text': {Permission.SCENE_READ, Permission.SCENE_UPDATE},
                'status': {Permission.SCENE_READ, Permission.SCENE_TRANSITION},
                'locked_by': {Permission.SCENE_READ, Permission.SCENE_LOCK},
                'positive_prompt': {Permission.SCENE_READ, Permission.SCENE_UPDATE},
                'negative_prompt': {Permission.SCENE_READ, Permission.SCENE_UPDATE},
                'generated_video_url': {Permission.SCENE_READ},
                'quality_metrics': {Permission.SCENE_READ},
            },
            'project': {
                'name': {Permission.PROJECT_READ},
                'description': {Permission.PROJECT_READ},
                'settings': {Permission.PROJECT_READ, Permission.PROJECT_UPDATE},
                'members': {Permission.PROJECT_READ, Permission.PROJECT_MANAGE_MEMBERS},
            },
        }
    
    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """獲取用戶上下文"""
        # TODO: 從數據庫加載
        return self.user_cache.get(user_id)
    
    def cache_user_context(self, context: UserContext):
        """緩存用戶上下文"""
        self.user_cache[context.user_id] = context
    
    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        檢查權限
        
        Args:
            user_id: 用戶 ID
            permission: 權限
            resource_type: 資源類型 (可選)
            resource_id: 資源 ID (可選)
            
        Returns:
            bool: 是否有權限
        """
        user_context = self.get_user_context(user_id)
        if not user_context or not user_context.is_active:
            return False
        
        # 1. 檢查角色權限
        if user_context.has_permission(permission):
            return True
        
        # 2. 檢查資源級權限
        if resource_type and resource_id:
            resource_key = f"{resource_type}:{resource_id}"
            if resource_key in self.resource_permissions:
                resource_perm = self.resource_permissions[resource_key].get(user_id)
                if resource_perm and permission in resource_perm.permissions:
                    # 檢查是否過期
                    if resource_perm.expires_at and datetime.utcnow() > resource_perm.expires_at:
                        return False
                    return True
        
        return False
    
    def grant_resource_permission(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
        permissions: Set[Permission],
        granted_by: str,
        expires_at: Optional[datetime] = None,
    ):
        """授予資源級權限"""
        resource_key = f"{resource_type}:{resource_id}"
        
        if resource_key not in self.resource_permissions:
            self.resource_permissions[resource_key] = {}
        
        self.resource_permissions[resource_key][user_id] = ResourcePermission(
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            permissions=permissions,
            granted_by=granted_by,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
        )
        
        logger.info(
            "permission_granted",
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            permissions=[p.value for p in permissions],
        )
    
    def revoke_resource_permission(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
    ):
        """撤銷資源級權限"""
        resource_key = f"{resource_type}:{resource_id}"
        
        if resource_key in self.resource_permissions and user_id in self.resource_permissions[resource_key]:
            del self.resource_permissions[resource_key][user_id]
            
            logger.info(
                "permission_revoked",
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
            )
    
    def check_field_permission(
        self,
        user_id: str,
        resource_type: str,
        field_name: str,
        operation: str,  # 'read', 'write'
    ) -> bool:
        """
        檢查字段級權限
        
        Args:
            user_id: 用戶 ID
            resource_type: 資源類型
            field_name: 字段名
            operation: 操作類型
            
        Returns:
            bool: 是否有權限
        """
        if resource_type not in self.field_permissions:
            return True  # 未配置則允許
        
        field_perms = self.field_permissions[resource_type].get(field_name)
        if not field_perms:
            return True  # 未配置則允許
        
        # 確定操作對應的權限
        required_permission = {
            'read': Permission.SCENE_READ,
            'write': Permission.SCENE_UPDATE,
        }.get(operation)
        
        if not required_permission:
            return False
        
        # 檢查是否有字段權限
        if required_permission not in field_perms:
            return True  # 字段未限制該操作
        
        # 檢查用戶權限
        return self.check_permission(user_id, required_permission, resource_type)
    
    def filter_fields(
        self,
        user_id: str,
        resource_type: str,
        data: Dict[str, Any],
        operation: str = 'read',
    ) -> Dict[str, Any]:
        """
        過濾字段 (根據權限)
        
        Args:
            user_id: 用戶 ID
            resource_type: 資源類型
            data: 原始數據
            operation: 操作類型
            
        Returns:
            過濾後的數據
        """
        if resource_type not in self.field_permissions:
            return data
        
        filtered = {}
        for field_name, value in data.items():
            if self.check_field_permission(user_id, resource_type, field_name, operation):
                filtered[field_name] = value
            else:
                logger.debug(
                    "field_filtered",
                    user_id=user_id,
                    resource_type=resource_type,
                    field_name=field_name,
                )
        
        return filtered
    
    def get_user_roles(self, user_id: str, project_id: Optional[str] = None) -> List[Role]:
        """獲取用戶角色"""
        user_context = self.get_user_context(user_id)
        if not user_context:
            return []
        
        # TODO: 如果是項目級別，需要檢查項目成員角色
        return user_context.roles


# ============================================================================
# FastAPI 依賴注入
# ============================================================================

async def get_current_user_context(
    # token: str = Depends(oauth2_scheme),
    # db: Session = Depends(get_db),
) -> UserContext:
    """
    獲取當前用戶上下文 (FastAPI 依賴)
    TODO: 實現 JWT Token 解析
    """
    # 模擬用戶上下文
    return UserContext(
        user_id="user-001",
        email="user@example.com",
        username="test_user",
        roles=[Role.EDITOR],
    )


async def require_permission(permission: Permission):
    """
    權限檢查依賴 (FastAPI)
    使用方式：@router.get(..., dependencies=[Depends(require_permission(Permission.SCENE_UPDATE))])
    """
    async def permission_checker(user: UserContext = Depends(get_current_user_context)):
        if not user.has_permission(permission):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}",
            )
        return user
    return permission_checker


# 全局服務實例
_rbac_service: Optional[RBACService] = None


def get_rbac_service() -> RBACService:
    """獲取 RBAC 服務單例"""
    global _rbac_service
    if not _rbac_service:
        _rbac_service = RBACService()
    return _rbac_service
