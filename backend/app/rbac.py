from fastapi import Depends, HTTPException
from psycopg.types.json import Jsonb
from .auth import require_user


def access(c, user_id):
    roles = [
        r["role_id"]
        for r in c.execute(
            "SELECT role_id FROM app_user_roles WHERE user_id=%s ORDER BY role_id",
            (user_id,),
        ).fetchall()
    ]
    permissions = [
        r["permission_id"]
        for r in c.execute(
            """SELECT DISTINCT p.permission_id FROM app_role_permissions p
        JOIN app_user_roles r ON r.role_id=p.role_id
        WHERE r.user_id=%s ORDER BY p.permission_id""",
            (user_id,),
        ).fetchall()
    ]
    return {"roles": roles or ["user"], "permissions": permissions}


def require_permission(permission):
    def check(user=Depends(require_user)):
        if permission not in user.get("permissions", []):
            raise HTTPException(403, "没有此管理功能的权限")
        return user

    return check


def audit(c, user, action, target, detail=None):
    c.execute(
        "INSERT INTO app_admin_audit(actor_id,action,target,detail) VALUES(%s,%s,%s,%s)",
        (user["id"], action, str(target), Jsonb(detail or {})),
    )
