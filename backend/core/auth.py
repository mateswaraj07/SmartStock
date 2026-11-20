"""Login for shop owners and suppliers (JWT). Passwords are hashed with PBKDF2."""
import datetime

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ShopOwner, Supplier


class Principal:
    """What request.user is: the role plus the ShopOwner or Supplier row."""
    is_authenticated = True

    def __init__(self, role, obj):
        self.role, self.obj = role, obj


def make_token(role, obj):
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    return jwt.encode({"role": role, "id": obj.id, "exp": exp}, settings.SECRET_KEY, algorithm="HS256")


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        try:
            data = jwt.decode(header[7:], settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError:
            raise AuthenticationFailed("Invalid or expired token.")
        model = ShopOwner if data.get("role") == "OWNER" else Supplier
        obj = model.objects.filter(pk=data.get("id")).first()
        if obj is None:
            raise AuthenticationFailed("Account not found.")
        return Principal(data["role"], obj), header[7:]

    def authenticate_header(self, request):
        return "Bearer"
