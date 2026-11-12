"""PasarGuard panel – strict real auth (API key / token) + groups + admin."""
from __future__ import annotations
import logging
import secrets
from typing import Any
import httpx

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
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        timeout: float = 20.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username
        self.password = password
        self._token = token
        self._api_key = token  # preferred: X-Api-Key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        if not self.base_url or not self.base_url.startswith(("http://", "https://")):
            raise PasarGuardAPIError("آدرس پنل نامعتبر است (باید با http:// یا https:// شروع شود)")
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
        if self._api_key:
            h["X-Api-Key"] = self._api_key
            h["Authorization"] = f"Bearer {self._api_key}"
        elif self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._client:
            raise PasarGuardAPIError("Client not initialized")
        path = path if path.startswith("/") else f"/{path}"
        try:
            r = await self._client.request(method, path, headers=self._headers(), **kwargs)
        except httpx.ConnectError as e:
            raise PasarGuardAPIError(f"اتصال برقرار نشد: {e}") from e
        except httpx.TimeoutException as e:
            raise PasarGuardAPIError(f"Timeout – پنل پاسخ نداد: {e}") from e
        except httpx.RequestError as e:
            raise PasarGuardAPIError(f"خطای شبکه: {e}") from e
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = (r.text or "")[:300]
            raise PasarGuardAPIError(f"HTTP {r.status_code}", status_code=r.status_code, detail=detail)
        if r.status_code == 204 or not r.content:
            return {}
        try:
            return r.json()
        except Exception:
            return {"raw": (r.text or "")[:200]}

    async def login(self) -> str:
        # If API key provided, just validate later via test_connection
        if self._api_key and not self.username:
            return self._api_key
        if not self.username or not self.password:
            if self._api_key:
                return self._api_key
            raise PasarGuardAPIError("API Key یا یوزرنیم/پسورد پاسارگارد الزامی است")

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
                errors.append(f"{path}→{r.status_code}")
            except Exception as e:
                errors.append(f"{path}→{e}")
        if self._api_key:
            return self._api_key
        raise PasarGuardAPIError(
            "لاگین پاسارگارد ناموفق. API Key را در فیلد توکن بگذارید یا یوزر/پسورد را چک کنید. "
            + " | ".join(errors[:3])
        )

    async def test_connection(self) -> dict:
        """Strict: must authenticate and hit a real admin endpoint."""
        try:
            if self._api_key:
                pass  # will validate with request
            elif self.username and self.password:
                await self.login()
            elif self._token:
                pass
            else:
                return {"ok": False, "error": "API Key (توکن) یا یوزرنیم/پسورد الزامی است"}

            last_err = None
            for path in (
                "/api/admin",
                "/api/system",
                "/api/admins?limit=1",
                "/api/groups",
                "/api/current",
            ):
                try:
                    data = await self._request("GET", path)
                    return {
                        "ok": True,
                        "path": path,
                        "stats": data if isinstance(data, dict) else {},
                        "authenticated": True,
                    }
                except PasarGuardAPIError as e:
                    last_err = e
                    if e.status_code in (401, 403):
                        return {
                            "ok": False,
                            "error": "احراز هویت رد شد (401/403) – API Key یا یوزر/پسورد اشتباه است",
                            "detail": e.detail,
                        }
                    continue
            return {
                "ok": False,
                "error": f"هیچ endpoint معتبری پاسخ نداد: {getattr(last_err, 'message', last_err)}",
                "detail": getattr(last_err, "detail", None),
            }
        except PasarGuardAPIError as e:
            return {"ok": False, "error": e.message, "detail": e.detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_groups(self) -> list[dict]:
        if not self._token and not self._api_key and self.username:
            await self.login()
        for path in ("/api/groups", "/api/group/s", "/api/group"):
            try:
                data = await self._request("GET", path)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    for key in ("groups", "items", "data", "results"):
                        if key in data and isinstance(data[key], list):
                            return data[key]
            except PasarGuardAPIError:
                continue
        return []

    async def list_services(self) -> list[dict]:
        return await self.list_groups()

    async def create_admin(
        self,
        username: str,
        password: str,
        is_sudo: bool = False,
        telegram_id: int | None = None,
        note: str | None = None,
        group_ids: list[int] | None = None,
        status: str = "active",
        **_kwargs,
    ) -> dict:
        if not self._token and not self._api_key and self.username:
            await self.login()
        payload: dict[str, Any] = {
            "username": username,
            "password": password,
            "is_sudo": False,
            "status": status,
        }
        if telegram_id:
            payload["telegram_id"] = telegram_id
        if note:
            payload["note"] = note
        if group_ids:
            payload["group_ids"] = group_ids
            payload["groups"] = group_ids
        last_err = None
        for path in ("/api/admin", "/api/admins"):
            try:
                return await self._request("POST", path, json=payload)
            except PasarGuardAPIError as e:
                last_err = e
                if e.status_code in (404, 405):
                    continue
                if e.status_code in (400, 422) and group_ids:
                    payload.pop("group_ids", None)
                    payload.pop("groups", None)
                    try:
                        return await self._request("POST", path, json=payload)
                    except PasarGuardAPIError:
                        pass
                raise
        raise last_err or PasarGuardAPIError("create_admin failed")

    async def modify_admin(self, username: str, **kwargs) -> dict:
        for path in (f"/api/admin/{username}", f"/api/admins/{username}"):
            try:
                return await self._request("PUT", path, json=kwargs)
            except PasarGuardAPIError as e:
                if e.status_code in (404, 405):
                    continue
                raise
        raise PasarGuardAPIError("modify_admin failed")

    async def delete_admin(self, username: str) -> None:
        for path in (f"/api/admin/{username}", f"/api/admins/{username}"):
            try:
                await self._request("DELETE", path)
                return
            except PasarGuardAPIError as e:
                if e.status_code in (404, 405):
                    continue
                raise

    async def disable_admin(self, username: str) -> None:
        try:
            await self.modify_admin(username, status="disabled")
            return
        except PasarGuardAPIError:
            pass
        dead = secrets.token_urlsafe(24)
        try:
            await self.modify_admin(username, password=dead, status="disabled")
        except PasarGuardAPIError:
            try:
                await self.modify_admin(username, password=dead)
            except PasarGuardAPIError:
                pass

    async def enable_admin(self, username: str, password: str) -> None:
        try:
            await self.modify_admin(username, password=password, status="active")
            return
        except PasarGuardAPIError:
            pass
        try:
            await self.modify_admin(username, password=password)
        except PasarGuardAPIError:
            pass

    async def get_users_of_admin(self, admin_username: str) -> list[dict]:
        for path in (
            f"/api/users?admin={admin_username}&limit=1000",
            f"/api/admin/users?admin={admin_username}&limit=1000",
            "/api/users?limit=1000",
        ):
            try:
                data = await self._request("GET", path)
                users = data.get("users") if isinstance(data, dict) else (data if isinstance(data, list) else [])
                if "admin=" not in path:
                    users = [
                        u
                        for u in (users or [])
                        if (u.get("admin") or {}).get("username") == admin_username
                        or u.get("admin") == admin_username
                        or u.get("created_by") == admin_username
                    ]
                return users or []
            except PasarGuardAPIError:
                continue
        return []

    async def disable_user(self, username: str) -> dict:
        for path in (f"/api/user/{username}", f"/api/users/{username}"):
            try:
                return await self._request("PUT", path, json={"status": "disabled"})
            except PasarGuardAPIError as e:
                if e.status_code in (404, 405):
                    continue
                raise
        return {}

    async def enable_user(self, username: str) -> dict:
        for path in (f"/api/user/{username}", f"/api/users/{username}"):
            try:
                return await self._request("PUT", path, json={"status": "active"})
            except PasarGuardAPIError as e:
                if e.status_code in (404, 405):
                    continue
                raise
        return {}

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
