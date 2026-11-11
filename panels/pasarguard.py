"""
PasarGuard Panel API Client
Auth: X-Api-Key header (preferred) or Bearer token from admin login
Docs: https://docs.pasarguard.org/
API paths commonly under /api/admin/...
"""
from __future__ import annotations
import httpx
from typing import Any
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class PasarGuardAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class PasarGuardPanel:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self._token: str | None = None
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=True,
            follow_redirects=True,
        )
        if not self.api_key and self.username and self.password:
            await self.login()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @property
    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["X-Api-Key"] = self.api_key
            # also support Authorization: apikey form
            h["Authorization"] = f"apikey {self.api_key}"
        elif self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._client:
            raise PasarGuardAPIError("Client not initialized")
        url = path if path.startswith("http") else path
        if not url.startswith("/"):
            url = "/" + url
        try:
            resp = await self._client.request(method, url, headers=self.headers, **kwargs)
        except httpx.RequestError as e:
            raise PasarGuardAPIError(f"Connection error: {e}") from e

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise PasarGuardAPIError(
                f"API error {resp.status_code}",
                status_code=resp.status_code,
                detail=detail,
            )
        if resp.status_code == 204:
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text

    async def login(self) -> str:
        """Fallback admin token login (Marzban-compatible)."""
        if not self._client:
            raise PasarGuardAPIError("Client not initialized")
        resp = await self._client.post(
            "/api/admin/token",
            data={"username": self.username, "password": self.password},
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            raise PasarGuardAPIError("Login failed", status_code=resp.status_code, detail=resp.text)
        result = resp.json()
        token = result.get("access_token") or result.get("token")
        if not token:
            raise PasarGuardAPIError("No token", detail=result)
        self._token = token
        return token

    async def test_connection(self) -> dict:
        for path in (
            "/api/system",
            "/api/admin/system",
            "/api/admin/users?limit=1",
            "/api/users?limit=1",
            "/api/admin/groups",
        ):
            try:
                data = await self._request("GET", path)
                return {"ok": True, "stats": data, "path": path}
            except PasarGuardAPIError:
                continue
        return {"ok": False, "error": "Could not reach any known system endpoint"}

    async def get_group_ids(self) -> list[int]:
        """Fetch available group IDs (required by many PasarGuard installs)."""
        for path in ("/api/admin/groups", "/api/groups", "/api/admin/groups/simple"):
            try:
                data = await self._request("GET", path)
                groups = []
                if isinstance(data, dict):
                    groups = data.get("groups") or data.get("items") or data.get("data") or []
                elif isinstance(data, list):
                    groups = data
                ids = []
                for g in groups:
                    if isinstance(g, dict) and "id" in g:
                        ids.append(int(g["id"]))
                    elif isinstance(g, int):
                        ids.append(g)
                if ids:
                    return ids
            except PasarGuardAPIError:
                continue
        return []

    async def create_user(
        self,
        username: str,
        data_limit_gb: int = 0,
        days: int = 30,
        note: str | None = None,
        status: str = "active",
        proxies: dict | None = None,
        group_ids: list[int] | None = None,
        **kwargs,
    ) -> dict:
        expire = 0
        if days and days > 0:
            expire = int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())
        data_limit = 0
        if data_limit_gb and data_limit_gb > 0:
            data_limit = int(data_limit_gb * 1024 * 1024 * 1024)

        if group_ids is None:
            group_ids = await self.get_group_ids()

        payload: dict[str, Any] = {
            "username": username,
            "status": status,
            "expire": expire,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset",
            "note": note or f"ROBIXA {datetime.now().isoformat()}",
        }
        if group_ids:
            payload["group_ids"] = group_ids
        if proxies:
            payload["proxies"] = proxies
        if kwargs.get("inbounds"):
            payload["inbounds"] = kwargs["inbounds"]

        last_err = None
        for path in ("/api/admin/users", "/api/user", "/api/users"):
            try:
                return await self._request("POST", path, json=payload)
            except PasarGuardAPIError as e:
                last_err = e
                if e.status_code in (404, 405, 422):
                    # 422 may mean missing required field; try next shape
                    continue
                raise
        raise last_err or PasarGuardAPIError("No create-user endpoint worked")

    async def get_user(self, username: str) -> dict:
        for path in (
            f"/api/admin/users/{username}",
            f"/api/user/{username}",
            f"/api/users/{username}",
        ):
            try:
                return await self._request("GET", path)
            except PasarGuardAPIError as e:
                if e.status_code == 404:
                    continue
                raise
        raise PasarGuardAPIError(f"User {username} not found")

    async def modify_user(self, username: str, **kwargs) -> dict:
        for path in (f"/api/admin/users/{username}", f"/api/user/{username}"):
            try:
                return await self._request("PUT", path, json=kwargs)
            except PasarGuardAPIError as e:
                if e.status_code in (404, 405):
                    continue
                raise
        raise PasarGuardAPIError("modify_user failed")

    async def disable_user(self, username: str) -> dict:
        return await self.modify_user(username, status="disabled")

    async def enable_user(self, username: str) -> dict:
        return await self.modify_user(username, status="active")

    async def delete_user(self, username: str) -> None:
        for path in (f"/api/admin/users/{username}", f"/api/user/{username}"):
            try:
                await self._request("DELETE", path)
                return
            except PasarGuardAPIError as e:
                if e.status_code in (404, 405):
                    continue
                raise
