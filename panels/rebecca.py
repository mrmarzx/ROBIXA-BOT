"""Rebecca panel client – reseller (non-sudo admin) + services."""
from __future__ import annotations
import logging
import secrets
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class RebeccaAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class RebeccaPanel:
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
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._client:
            raise RebeccaAPIError("Client not initialized")
        path = path if path.startswith("/") else f"/{path}"
        if not path.startswith("/api"):
            path = f"/api{path}"
        try:
            r = await self._client.request(method, path, headers=self._headers(), **kwargs)
        except httpx.RequestError as e:
            raise RebeccaAPIError(f"Connection error: {e}") from e
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RebeccaAPIError(f"HTTP {r.status_code}", status_code=r.status_code, detail=detail)
        if r.status_code == 204 or not r.content:
            return {}
        try:
            return r.json()
        except Exception:
            return {"raw": r.text}

    async def login(self) -> str:
        for path in ("/api/admin/token", "/api/admins/token", "/api/token"):
            try:
                data = await self._request(
                    "POST", path,
                    data={"username": self.username, "password": self.password}
                    if "token" in path else None,
                    json={"username": self.username, "password": self.password},
                )
                token = data.get("access_token") or data.get("token")
                if token:
                    self._token = token
                    return token
            except RebeccaAPIError:
                continue
        # form style
        try:
            r = await self._client.post(
                "/api/admin/token",
                data={"username": self.username, "password": self.password, "grant_type": "password"},
                headers={"Accept": "application/json"},
            )
            if r.status_code < 400:
                data = r.json()
                token = data.get("access_token") or data.get("token")
                if token:
                    self._token = token
                    return token
        except Exception:
            pass
        raise RebeccaAPIError("Login failed – check credentials")

    async def test_connection(self) -> dict:
        try:
            if not self._token and self.username and self.password:
                await self.login()
            for path in ("/system", "/admin", "/admins?limit=1", "/services"):
                try:
                    stats = await self._request("GET", path)
                    return {"ok": True, "stats": stats}
                except RebeccaAPIError:
                    continue
            return {"ok": True, "stats": {}}
        except RebeccaAPIError as e:
            return {"ok": False, "error": str(e), "detail": e.detail}

    async def list_services(self) -> list[dict]:
        """Return list of panel services: [{id, name, ...}, ...]"""
        for path in ("/services", "/service", "/api/services"):
            try:
                data = await self._request("GET", path if path.startswith("/api") else path)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    for key in ("services", "items", "data", "results"):
                        if key in data and isinstance(data[key], list):
                            return data[key]
            except RebeccaAPIError:
                continue
        return []

    async def create_admin(
        self,
        username: str,
        password: str,
        is_sudo: bool = False,
        telegram_id: int | None = None,
        note: str | None = None,
        service_ids: list[int] | None = None,
        permissions: dict | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "username": username,
            "password": password,
            "is_sudo": False,
            "role": "admin",
        }
        if telegram_id:
            payload["telegram_id"] = telegram_id
        if note:
            payload["note"] = note
        if service_ids:
            payload["services"] = service_ids
        if permissions:
            payload["permissions"] = permissions
        try:
            return await self._request("POST", "/admin", json=payload)
        except RebeccaAPIError as e:
            if e.status_code in (400, 422):
                # retry minimal
                minimal = {
                    "username": username,
                    "password": password,
                    "is_sudo": False,
                }
                if service_ids:
                    minimal["services"] = service_ids
                return await self._request("POST", "/admin", json=minimal)
            raise

    async def modify_admin(self, username: str, **kwargs) -> dict:
        return await self._request("PUT", f"/admin/{username}", json=kwargs)

    async def delete_admin(self, username: str) -> None:
        await self._request("DELETE", f"/admin/{username}")

    async def disable_admin(self, username: str) -> None:
        dead_pass = secrets.token_urlsafe(24)
        for kwargs in (
            {"password": dead_pass, "is_sudo": False, "status": "disabled"},
            {"password": dead_pass, "status": "disabled"},
            {"password": dead_pass},
        ):
            try:
                await self.modify_admin(username, **kwargs)
                return
            except RebeccaAPIError:
                continue

    async def enable_admin(self, username: str, password: str) -> None:
        for kwargs in (
            {"password": password, "is_sudo": False, "status": "active"},
            {"password": password, "status": "active"},
            {"password": password},
        ):
            try:
                await self.modify_admin(username, **kwargs)
                return
            except RebeccaAPIError:
                continue

    async def get_users_of_admin(self, admin_username: str) -> list[dict]:
        try:
            data = await self._request("GET", f"/users?admin={admin_username}&limit=1000")
            if isinstance(data, dict):
                return data.get("users") or data.get("items") or []
            if isinstance(data, list):
                return data
        except RebeccaAPIError:
            pass
        try:
            data = await self._request("GET", "/users?limit=1000")
            users = data.get("users") if isinstance(data, dict) else (data or [])
            out = []
            for u in users or []:
                adm = u.get("admin")
                if isinstance(adm, dict) and adm.get("username") == admin_username:
                    out.append(u)
                elif adm == admin_username or u.get("created_by") == admin_username:
                    out.append(u)
            return out
        except RebeccaAPIError:
            return []

    async def disable_user(self, username: str) -> dict:
        try:
            return await self._request("PUT", f"/user/{username}", json={"status": "disabled"})
        except RebeccaAPIError:
            return await self._request("PUT", f"/users/{username}", json={"status": "disabled"})

    async def enable_user(self, username: str) -> dict:
        try:
            return await self._request("PUT", f"/user/{username}", json={"status": "active"})
        except RebeccaAPIError:
            return await self._request("PUT", f"/users/{username}", json={"status": "active"})

    async def disable_users(self, usernames: list[str]) -> list[str]:
        done = []
        for u in usernames:
            try:
                await self.disable_user(u)
                done.append(u)
            except Exception as e:
                logger.warning("disable user %s: %s", u, e)
        return done

    async def enable_users(self, usernames: list[str]) -> list[str]:
        done = []
        for u in usernames:
            try:
                await self.enable_user(u)
                done.append(u)
            except Exception as e:
                logger.warning("enable user %s: %s", u, e)
        return done

    def dashboard_url(self) -> str:
        return f"{self.base_url}/dashboard/"
