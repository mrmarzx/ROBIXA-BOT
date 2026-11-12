"""Marzban panel client – reseller admin + user templates."""
from __future__ import annotations
import logging
import secrets
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class MarzbanAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class MarzbanPanel:
    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token = token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=False,
            follow_redirects=True,
        )
        if not self._token and self.username and self.password:
            await self.login()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._client:
            raise MarzbanAPIError("Client not initialized")
        path = path if path.startswith("/") else f"/{path}"
        if not path.startswith("/api"):
            path = f"/api{path}"
        headers = self._headers()
        if method.upper() in ("POST", "PUT", "PATCH") and "json" in kwargs:
            headers["Content-Type"] = "application/json"
        try:
            r = await self._client.request(method, path, headers=headers, **kwargs)
        except httpx.RequestError as e:
            raise MarzbanAPIError(f"Connection error: {e}") from e
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise MarzbanAPIError(f"HTTP {r.status_code}", status_code=r.status_code, detail=detail)
        if r.status_code == 204 or not r.content:
            return {}
        try:
            return r.json()
        except Exception:
            return {"raw": r.text}

    async def login(self) -> str:
        r = await self._client.post(
            "/api/admin/token",
            data={"username": self.username, "password": self.password, "grant_type": "password"},
            headers={"Accept": "application/json"},
        )
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise MarzbanAPIError(f"Login failed HTTP {r.status_code}", status_code=r.status_code, detail=detail)
        data = r.json()
        token = data.get("access_token")
        if not token:
            raise MarzbanAPIError("No access_token in response")
        self._token = token
        return token

    async def test_connection(self) -> dict:
        try:
            if not self._token and self.username and self.password:
                await self.login()
            stats = await self._request("GET", "/system")
            return {"ok": True, "stats": stats}
        except MarzbanAPIError as e:
            return {"ok": False, "error": str(e), "detail": e.detail}

    async def list_templates(self) -> list[dict]:
        """User templates: [{id, name, inbounds, data_limit, expire_duration}, ...]"""
        try:
            data = await self._request("GET", "/user_template")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("templates") or data.get("items") or []
        except MarzbanAPIError:
            pass
        return []

    async def get_template_by_name(self, name: str) -> dict | None:
        templates = await self.list_templates()
        name_l = (name or "").strip().lower()
        for t in templates:
            if (t.get("name") or "").strip().lower() == name_l:
                return t
        return None

    async def list_services(self) -> list[dict]:
        """Marzban equivalent – user templates shown as services."""
        return await self.list_templates()

    async def create_admin(
        self,
        username: str,
        password: str,
        is_sudo: bool = False,
        telegram_id: int | None = None,
        note: str | None = None,
        template_id: int | None = None,
        template_name: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "username": username,
            "password": password,
            "is_sudo": False,
        }
        if telegram_id:
            payload["telegram_id"] = telegram_id
        # Marzban admin create – template is used by reseller when creating users;
        # store association on our side via extra_config
        return await self._request("POST", "/admin", json=payload)

    async def modify_admin(self, username: str, **kwargs) -> dict:
        return await self._request("PUT", f"/admin/{username}", json=kwargs)

    async def delete_admin(self, username: str) -> None:
        await self._request("DELETE", f"/admin/{username}")

    async def disable_admin(self, username: str) -> None:
        dead_pass = secrets.token_urlsafe(24)
        try:
            await self.modify_admin(username, password=dead_pass, is_sudo=False)
        except MarzbanAPIError:
            pass

    async def enable_admin(self, username: str, password: str) -> None:
        await self.modify_admin(username, password=password, is_sudo=False)

    async def get_users_of_admin(self, admin_username: str) -> list[dict]:
        try:
            data = await self._request("GET", f"/users?admin={admin_username}&limit=1000")
            if isinstance(data, dict):
                return data.get("users") or []
            if isinstance(data, list):
                return data
        except MarzbanAPIError:
            pass
        try:
            data = await self._request("GET", "/users?limit=1000")
            users = data.get("users") if isinstance(data, dict) else (data or [])
            return [
                u
                for u in users
                if (u.get("admin") or {}).get("username") == admin_username
                or u.get("admin") == admin_username
            ]
        except MarzbanAPIError:
            return []

    async def disable_user(self, username: str) -> dict:
        return await self._request("PUT", f"/user/{username}", json={"status": "disabled"})

    async def enable_user(self, username: str) -> dict:
        return await self._request("PUT", f"/user/{username}", json={"status": "active"})

    async def disable_users(self, usernames: list[str]) -> list[str]:
        done = []
        for u in usernames:
            try:
                await self.disable_user(u)
                done.append(u)
            except Exception as e:
                logger.warning("disable user %s failed: %s", u, e)
        return done

    async def enable_users(self, usernames: list[str]) -> list[str]:
        done = []
        for u in usernames:
            try:
                await self.enable_user(u)
                done.append(u)
            except Exception as e:
                logger.warning("enable user %s failed: %s", u, e)
        return done

    def dashboard_url(self) -> str:
        return f"{self.base_url}/dashboard/"
