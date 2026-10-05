"""Autenticación: registro, login, refresco de token y perfil."""
from __future__ import annotations

from flask import Blueprint, request
from flask.wrappers import Response
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User, UserRole
from ..schemas import LoginSchema, RegisterSchema, UserSchema
from . import current_user, error, success

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

register_schema = RegisterSchema()
login_schema = LoginSchema()
user_schema = UserSchema()


def _token_pair(user: User) -> dict[str, object]:
    identity = str(user.id)
    claims = {"role": user.role.value}
    return {
        "access_token": create_access_token(identity=identity, additional_claims=claims),
        "refresh_token": create_refresh_token(identity=identity, additional_claims=claims),
        "token_type": "Bearer",
        "user": user_schema.dump(user),
    }


@auth_bp.post("/register")
def register() -> tuple[Response, int]:
    """Registro público.

    Reglas de rol:
      * El primer usuario del sistema se crea como Admin.
      * Solo un Admin autenticado puede asignar un rol distinto de Employee.
    """
    data = register_schema.load(request.get_json(silent=True) or {})

    requested_role: UserRole = data["role"]
    is_first_user = (db.session.scalar(select(func.count(User.id))) or 0) == 0
    if is_first_user:
        role = UserRole.ADMIN
    else:
        role = UserRole.EMPLOYEE
        if requested_role != UserRole.EMPLOYEE:
            verify_jwt_in_request(optional=True)
            if get_jwt_identity() is None or current_user().role != UserRole.ADMIN:
                return error("Solo un administrador puede asignar ese rol.", 403)
            role = requested_role

    if db.session.scalar(select(User).filter_by(email=data["email"])):
        return error("Ya existe un usuario con ese email.", 409)

    user = User(email=data["email"], full_name=data.get("full_name"), role=role)
    user.set_password(data["password"])
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("Ya existe un usuario con ese email.", 409)

    return success(_token_pair(user), 201, "Usuario registrado correctamente.")


@auth_bp.post("/login")
def login() -> tuple[Response, int]:
    data = login_schema.load(request.get_json(silent=True) or {})
    user = db.session.scalar(select(User).filter_by(email=data["email"]))
    # Mensaje genérico para no revelar si el email existe.
    if user is None or not user.check_password(data["password"]):
        return error("Credenciales incorrectas.", 401)
    if not user.is_active:
        return error("La cuenta está desactivada.", 403)
    return success(_token_pair(user))


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh() -> tuple[Response, int]:
    user = current_user()
    return success(
        {
            "access_token": create_access_token(
                identity=str(user.id), additional_claims={"role": user.role.value}
            ),
            "token_type": "Bearer",
        }
    )


@auth_bp.get("/me")
@jwt_required()
def me() -> tuple[Response, int]:
    return success(user_schema.dump(current_user()))
