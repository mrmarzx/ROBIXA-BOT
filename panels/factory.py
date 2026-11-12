"""Unified panel factory for reseller (admin) operations."""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Any

from panels.rebecca import RebeccaPanel, RebeccaAPIError
from panels.marzban import MarzbanPanel, MarzbanAPIError
from panels.pasarguard import PasarGuardPanel, PasarGuardAPIError


class PanelError(Exception):
    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


@asynccontextmanager
async def _client(panel_type: str, base_url: str, panel_username, panel_password, token):
    ptype = (panel_type or "").upper()
    if ptype == "REBECCA":
        async with RebeccaPanel(base_url, panel_username, panel_password, token) as api:
            yield api
    elif ptype == "MARZBAN":
        async with MarzbanPanel(base_url, panel_username, panel_password, token) as api:
            yield api
    elif ptype == "PASARGUARD":
        async with PasarGuardPanel(base_url, panel_username, panel_password, token) as api:
            yield api
    else:
        raise PanelError(f"Unknown panel type: {panel_type}")


async def test_panel_connection(
    panel_type: str,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
) -> dict:
    try:
        async with _client(panel_type, base_url, username, password, token) as api:
            return await api.test_connection()
    except (RebeccaAPIError, MarzbanAPIError, PasarGuardAPIError) as e:
        return {"ok": False, "error": e.message, "detail": getattr(e, "detail", None)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def list_panel_services(
    panel_type: str,
    base_url: str,
    panel_username: str | None = None,
    panel_password: str | None = None,
    token: str | None = None,
) -> list[dict]:
    """
    Unified list of selectable 'services' for the panel:
    - REBECCA  → services (id, name)
    - PASARGUARD → groups (id, name)
    - MARZBAN → user templates (id, name)
    Each item normalized to {id, name, raw}
    """
    ptype = (panel_type or "").upper()
    try:
        async with _client(panel_type, base_url, panel_username, panel_password, token) as api:
            if ptype == "REBECCA":
                items = await api.list_services()
            elif ptype == "PASARGUARD":
                items = await api.list_groups()
            elif ptype == "MARZBAN":
                items = await api.list_templates()
            else:
                items = []
    except Exception as e:
        raise PanelError(str(e)) from e

    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        iid = it.get("id")
        name = it.get("name") or it.get("title") or str(iid)
        out.append({"id": iid, "name": name, "raw": it})
    return out


async def create_reseller_on_panel(
    panel_type: str,
    base_url: str,
    username: str,
    password: str,
    panel_username: str | None = None,
    panel_password: str | None = None,
    token: str | None = None,
    telegram_id: int | None = None,
    note: str | None = None,
    extra_config: dict | None = None,
) -> dict:
    """
    Create a non-sudo admin (نمایندگی).
    extra_config may contain:
      service_ids / service_id  (Rebecca)
      group_ids / group_id      (PasarGuard)
      template_id / template_name (Marzban – stored for reference)
    """
    extra = extra_config or {}
    ptype = (panel_type or "").upper()
    try:
        async with _client(panel_type, base_url, panel_username, panel_password, token) as api:
            kwargs: dict[str, Any] = {
                "username": username,
                "password": password,
                "is_sudo": False,
                "telegram_id": telegram_id,
                "note": note,
            }
            if ptype == "REBECCA":
                sids = extra.get("service_ids") or []
                if not sids and extra.get("service_id") is not None:
                    sids = [extra["service_id"]]
                if sids:
                    kwargs["service_ids"] = [int(x) for x in sids]
            elif ptype == "PASARGUARD":
                gids = extra.get("group_ids") or []
                if not gids and extra.get("group_id") is not None:
                    gids = [extra["group_id"]]
                if gids:
                    kwargs["group_ids"] = [int(x) for x in gids]
            elif ptype == "MARZBAN":
                if extra.get("template_id") is not None:
                    kwargs["template_id"] = extra["template_id"]
                if extra.get("template_name"):
                    kwargs["template_name"] = extra["template_name"]

            result = await api.create_admin(**kwargs)
            dash = api.dashboard_url()
            if isinstance(result, dict):
                result["dashboard_url"] = dash
                result.setdefault("username", username)
            else:
                result = {"username": username, "dashboard_url": dash, "raw": result}
            return result
    except (RebeccaAPIError, MarzbanAPIError, PasarGuardAPIError) as e:
        raise PanelError(e.message, detail=getattr(e, "detail", None)) from e
    except PanelError:
        raise
    except Exception as e:
        raise PanelError(str(e)) from e


async def disable_reseller_on_panel(
    panel_type: str,
    base_url: str,
    admin_username: str,
    panel_username: str | None = None,
    panel_password: str | None = None,
    token: str | None = None,
) -> list[str]:
    """Expire: disable active users of admin + lock admin. Returns snapshot usernames."""
    async with _client(panel_type, base_url, panel_username, panel_password, token) as api:
        users = await api.get_users_of_admin(admin_username)
        active_names = []
        for u in users:
            status = (u.get("status") or "").lower()
            name = u.get("username")
            if not name:
                continue
            if status in ("disabled", "expired", "limited"):
                continue
            active_names.append(name)

        disabled = await api.disable_users(active_names)
        try:
            await api.disable_admin(admin_username)
        except Exception:
            pass
        return disabled


async def enable_reseller_on_panel(
    panel_type: str,
    base_url: str,
    admin_username: str,
    password: str,
    users_to_enable: list[str],
    panel_username: str | None = None,
    panel_password: str | None = None,
    token: str | None = None,
) -> list[str]:
    """Renew: restore admin + re-enable only snapshot users."""
    async with _client(panel_type, base_url, panel_username, panel_password, token) as api:
        try:
            await api.enable_admin(admin_username, password)
        except Exception:
            pass
        if not users_to_enable:
            return []
        return await api.enable_users(users_to_enable)


# backward-compatible aliases
async def create_user_on_panel(*args, **kwargs):
    raise PanelError("این ربات فروش نمایندگی است نه کانفیگ.")


async def disable_user_on_panel(*args, **kwargs):
    raise PanelError("از disable_reseller_on_panel استفاده کنید.")
