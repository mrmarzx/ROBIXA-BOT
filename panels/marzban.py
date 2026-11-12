"""Marzban panel – strict real auth + admin (reseller) ops."""
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
            raise MarzbanAPIError("آدرس پنل نامعتبر است (باید با http:// یا https:// شروع شود)")
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
        except httpx.ConnectError as e:
            raise MarzbanAPIError(f"اتصال برقرار نشد: {e}") from e
        except httpx.TimeoutException as e:
            raise MarzbanAPIError(f"Timeout – پنل پاسخ نداد: {e}") from e
        except httpx.RequestError as e:
            raise MarzbanAPIError(f"خطای شبکه: {e}") from e
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = (r.text or "")[:300]
            raise MarzbanAPIError(
                f"HTTP {r.status_code}", status_code=r.status_code, detail=detail
            )
        if r.status_code == 204 or not r.content:
            return {}
        try:
            return r.json()
        except Exception:
            return {"raw": (r.text or "")[:200]}

    async def login(self) -> str:
        if not self.username or not self.password:
            raise MarzbanAPIError("یوزرنیم و پسورد مرزبان الزامی است")
        try:
            r = await self._client.post(
                "/api/admin/token",
                data={
                    "username": self.username,
                    "password": self.password,
                    "grant_type": "password",
                },
                headers={"Accept": "application/json"},
            )
        except httpx.ConnectError as e:
            raise MarzbanAPIError(f"اتصال به پنل برقرار نشد: {e}") from e
        except httpx.TimeoutException:
            raise MarzbanAPIError("Timeout هنگام لاگین – آدرس یا فایروال را چک کنید")
        except httpx.RequestError as e:
            raise MarzbanAPIError(f"خطای شبکه هنگام لاگین: {e}") from e

        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = (r.text or "")[:300]
            raise MarzbanAPIError(
                f"لاگین ناموفق HTTP {r.status_code} – یوزر/پسورد اشتباه یا پنل در دسترس نیست",
                status_code=r.status_code,
                detail=detail,
            )
        try:
            data = r.json()
        except Exception as e:
            raise MarzbanAPIError("پاسخ لاگین JSON نیست – آدرس پنل اشتباه است؟") from e
        token = data.get("access_token")
        if not token:
            raise MarzbanAPIError("توکن در پاسخ لاگین نبود – پنل مرزبان نیست یا نسخه متفاوت است")
        self._token = token
        return token

    async def test_connection(self) -> dict:
        """Strict: must login (or use token) AND call authenticated /api/admin or /api/system."""
        try:
            if self._token:
                # validate existing token
                pass
            elif self.username and self.password:
                await self.login()
            else:
                return {"ok": False, "error": "یوزرنیم/پسورد یا توکن الزامی است"}

            # Must succeed on an authenticated endpoint
            last_err = None
            for path in ("/admin", "/system", "/admins"):
                try:
                    data = await self._request("GET", path)
                    return {
                        "ok": True,
                        "path": path,
                        "stats": data if isinstance(data, dict) else {},
                        "authenticated": True,
                    }
                except MarzbanAPIError as e:
                    last_err = e
                    if e.status_code in (401, 403):
                        return {
                            "ok": False,
                            "error": "احراز هویت رد شد (401/403) – یوزر/پسورد یا توکن اشتباه است",
                            "detail": e.detail,
                        }
                    continue
            return {
                "ok": False,
                "error": f"هیچ endpoint معتبری پاسخ نداد: {getattr(last_err, 'message', last_err)}",
                "detail": getattr(last_err, "detail", None),
            }
        except MarzbanAPIError as e:
            return {"ok": False, "error": e.message, "detail": e.detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_templates(self) -> list[dict]:
        data = await self._request("GET", "/user_template")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("templates") or data.get("items") or []
        return []

    async def list_services(self) -> list[dict]:
        return await self.list_templates()

    async def get_template_by_name(self, name: str) -> dict | None:
        name_l = (name or "").strip().lower()
        for t in await self.list_templates():
            if (t.get("name") or "").strip().lower() == name_l:
                return t
        return None

    async def create_admin(
        self,
        username: str,
        password: str,
        is_sudo: bool = False,
        telegram_id: int | None = None,
        note: str | None = None,
        template_id: int | None = None,
        template_name: str | None = None,
        **_kwargs,
    ) -> dict:
        if not self._token:
            await self.login()
        payload: dict[str, Any] = {
            "username": username,
            "password": password,
            "is_sudo": False,
        }
        if telegram_id:
            payload["telegram_id"] = telegram_id
        return await self._request("POST", "/admin", json=payload)

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
        try:
            await self.modify_admin(username, password=dead, is_sudo=False)
        except MarzbanAPIError:
            pass

    async def enable_admin(self, username: str, password: str) -> None:
        await self.modify_admin(username, password=password, is_sudo=False)

    async def get_users_of_admin(self, admin_username: str) -> list[dict]:
        if not self._token:
            await self.login()
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
