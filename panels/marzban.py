"""Marzban Panel API Client (official REST API)"""
from __future__ import annotations
import httpx
from typing import Any
from datetime import datetime, timedelta, timezone
import logging

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
            verify=True,
            follow_redirects=True,
        )
        if not self._token and self.username and self.password:
            await self.login()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @property
    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._client:
            raise MarzbanAPIError("Client not initialized")
        url = path if path.startswith("http") else f"/api{path}"
        try:
            resp = await self._client.request(method, url, headers=self.headers, **kwargs)
        except httpx.RequestError as e:
            raise MarzbanAPIError(f"Connection error: {e}") from e

        if resp.status_code == 401 and self.username and self.password:
            await self.login()
            resp = await self._client.request(method, url, headers=self.headers, **kwargs)

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise MarzbanAPIError(
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
        # Marzban uses form data for /api/admin/token
        if not self._client:
            raise MarzbanAPIError("Client not initialized")
        resp = await self._client.post(
            "/api/admin/token",
            data={"username": self.username, "password": self.password},
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            raise MarzbanAPIError("Login failed", status_code=resp.status_code, detail=resp.text)
        result = resp.json()
        token = result.get("access_token") or result.get("token")
        if not token:
            raise MarzbanAPIError("No token in login response", detail=result)
        self._token = token
        return token

    async def test_connection(self) -> dict:
        try:
            stats = await self._request("GET", "/system")
            return {"ok": True, "stats": stats}
        except MarzbanAPIError as e:
            return {"ok": False, "error": str(e), "detail": e.detail}

    async def create_user(
        self,
        username: str,
        data_limit_gb: int = 0,
        days: int = 30,
        proxies: dict | None = None,
        inbounds: dict | None = None,
        note: str | None = None,
        status: str = "active",
    ) -> dict:
        expire = 0
        if days and days > 0:
            expire = int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())
        data_limit = 0
        if data_limit_gb and data_limit_gb > 0:
            data_limit = int(data_limit_gb * 1024 * 1024 * 1024)
        if proxies is None:
            proxies = {"vless": {}, "vmess": {}, "trojan": {}, "shadowsocks": {}}
        payload = {
            "username": username,
            "proxies": proxies,
            "inbounds": inbounds or {},
            "expire": expire,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset",
            "status": status,
            "note": note or f"ROBIXA {datetime.now().isoformat()}",
        }
        return await self._request("POST", "/user", json=payload)

    async def get_user(self, username: str) -> dict:
        return await self._request("GET", f"/user/{username}")

    async def modify_user(self, username: str, **kwargs) -> dict:
        return await self._request("PUT", f"/user/{username}", json=kwargs)

    async def delete_user(self, username: str) -> None:
        await self._request("DELETE", f"/user/{username}")

    async def disable_user(self, username: str) -> dict:
        return await self.modify_user(username, status="disabled")

    async def enable_user(self, username: str) -> dict:
        return await self.modify_user(username, status="active")
