"""Rebecca panel – strict real auth + services + admin (reseller)."""
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
        timeout: float = 20.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username
        self.password = password
        self._token = token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        if not self.base_url or not self.base_url.startswith(("http://", "https://")):
            raise RebeccaAPIError("آدرس پنل نامعتبر است (باید با http:// یا https:// شروع شود)")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            verify=False,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
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
        except httpx.ConnectError as e:
            raise RebeccaAPIError(f"اتصال برقرار نشد: {e}") from e
        except httpx.TimeoutException as e:
            raise RebeccaAPIError(f"Timeout – پنل پاسخ نداد: {e}") from e
        except httpx.RequestError as e:
            raise RebeccaAPIError(f"خطای شبکه: {e}") from e
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = (r.text or "")[:300]
            raise RebeccaAPIError(f"HTTP {r.status_code}", status_code=r.status_code, detail=detail)
        if r.status_code == 204 or not r.content:
            return {}
        try:
            return r.json()
        except Exception:
            return {"raw": (r.text or "")[:200]}

    async def login(self) -> str:
        if not self.username or not self.password:
            raise RebeccaAPIError("یوزرنیم و پسورد ربکا الزامی است")
        # Try form token (OAuth2 style) then JSON
        errors = []
        for path in ("/api/admin/token", "/api/admins/token", "/api/token"):
            try:
                r = await self._client.post(
                    path,
                    data={
                        "username": self.username,
                        "password": self.password,
                        "grant_type": "password",
                    },
                    headers={"Accept": "application/json"},
                )
                if r.status_code < 400:
                    data = r.json()
                    token = data.get("access_token") or data.get("token")
                    if token:
                        self._token = token
                        return token
                errors.append(f"{path} form→{r.status_code}")
            except Exception as e:
                errors.append(f"{path} form→{e}")
            try:
                r = await self._client.post(
                    path,
                    json={"username": self.username, "password": self.password},
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                )
                if r.status_code < 400:
                    data = r.json()
                    token = data.get("access_token") or data.get("token")
                    if token:
                        self._token = token
                        return token
                errors.append(f"{path} json→{r.status_code}")
            except Exception as e:
                errors.append(f"{path} json→{e}")
        raise RebeccaAPIError(
            "لاگین ربکا ناموفق – یوزر/پسورد اشتباه یا آدرس پنل غلط است. "
            + " | ".join(errors[:4])
        )

    async def test_connection(self) -> dict:
        """Strict: login required + authenticated endpoint must succeed."""
        try:
            if not self._token:
                if self.username and self.password:
                    await self.login()
                else:
                    return {"ok": False, "error": "یوزرنیم/پسورد یا توکن الزامی است"}

            last_err = None
            for path in ("/admin", "/system", "/admins?limit=1", "/services"):
                try:
                    data = await self._request("GET", path)
                    return {
                        "ok": True,
                        "path": path,
                        "stats": data if isinstance(data, dict) else {},
                        "authenticated": True,
                    }
                except RebeccaAPIError as e:
                    last_err = e
                    if e.status_code in (401, 403):
                        return {
                            "ok": False,
                            "error": "احراز هویت رد شد (401/403) – مشخصات ورود اشتباه است",
                            "detail": e.detail,
                        }
                    continue
            return {
                "ok": False,
                "error": f"هیچ endpoint معتبری پاسخ نداد: {getattr(last_err, 'message', last_err)}",
                "detail": getattr(last_err, "detail", None),
            }
        except RebeccaAPIError as e:
            return {"ok": False, "error": e.message, "detail": e.detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_services(self) -> list[dict]:
        if not self._token:
            await self.login()
        for path in ("/services", "/service"):
            try:
                data = await self._request("GET", path)
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
        **_kwargs,
    ) -> dict:
        if not self._token:
            await self.login()
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
                minimal = {"username": username, "password": password, "is_sudo": False}
                if service_ids:
                    minimal["services"] = service_ids
                return await self._request("POST", "/admin", json=minimal)
            raise

    async def modify_admin(self, username: str, **kwargs) -> dict:
        if not self._token:
            await self.login()
        return await self._request("PUT", f"/admin/{username}", json=kwargs)

    async def delete_admin(self, username: str) -> None:
        if not self._token:
            await self.login()
        await self._request("DELETE", f"/admin/{username}")

    async def disable_admin(self, username: str) -> None:
        dead = secrets.token_urlsafe(24)
        for kwargs in (
            {"password": dead, "is_sudo": False, "status": "disabled"},
            {"password": dead, "status": "disabled"},
            {"password": dead},
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
        if not self._token:
            await self.login()
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
