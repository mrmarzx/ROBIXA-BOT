"""
Unified panel factory – create users on Rebecca / Marzban / PasarGuard
"""
from __future__ import annotations
from typing import Any
from panels.rebecca import RebeccaPanel, RebeccaAPIError
from panels.marzban import MarzbanPanel, MarzbanAPIError
from panels.pasarguard import PasarGuardPanel, PasarGuardAPIError


class PanelError(Exception):
    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


async def test_panel_connection(
    panel_type: str,
    base_url: str,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
) -> dict:
    ptype = (panel_type or "").upper()
    try:
        if ptype == "REBECCA":
            async with RebeccaPanel(base_url, username, password, token) as api:
                return await api.test_connection()
        if ptype == "MARZBAN":
            async with MarzbanPanel(base_url, username, password, token) as api:
                return await api.test_connection()
        if ptype in ("PASARGUARD", "PASURGARD", "PASARGAD"):
            # token field used as API key for PasarGuard
            async with PasarGuardPanel(base_url, api_key=token, username=username, password=password) as api:
                return await api.test_connection()
        return {"ok": False, "error": f"Unknown panel type: {panel_type}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def create_user_on_panel(
    panel_type: str,
    base_url: str,
    username: str,
    data_limit_gb: int,
    days: int,
    panel_username: str | None = None,
    panel_password: str | None = None,
    token: str | None = None,
    note: str | None = None,
) -> dict:
    """
    Create proxy user on the given panel type.
    Returns panel response dict or raises PanelError.
    """
    ptype = (panel_type or "").upper()
    try:
        if ptype == "REBECCA":
            async with RebeccaPanel(base_url, panel_username, panel_password, token) as api:
                return await api.create_user(
                    username=username,
                    data_limit_gb=data_limit_gb,
                    days=days,
                    note=note,
                )
        if ptype == "MARZBAN":
            async with MarzbanPanel(base_url, panel_username, panel_password, token) as api:
                return await api.create_user(
                    username=username,
                    data_limit_gb=data_limit_gb,
                    days=days,
                    note=note,
                )
        if ptype in ("PASARGUARD", "PASURGARD", "PASARGAD"):
            async with PasarGuardPanel(
                base_url, api_key=token, username=panel_username, password=panel_password
            ) as api:
                return await api.create_user(
                    username=username,
                    data_limit_gb=data_limit_gb,
                    days=days,
                    note=note,
                )
        raise PanelError(f"Unsupported panel type: {panel_type}")
    except (RebeccaAPIError, MarzbanAPIError, PasarGuardAPIError) as e:
        raise PanelError(e.message, detail=getattr(e, "detail", None)) from e
    except PanelError:
        raise
    except Exception as e:
        raise PanelError(str(e)) from e


async def disable_user_on_panel(
    panel_type: str,
    base_url: str,
    username: str,
    panel_username: str | None = None,
    panel_password: str | None = None,
    token: str | None = None,
) -> None:
    ptype = (panel_type or "").upper()
    if ptype == "REBECCA":
        async with RebeccaPanel(base_url, panel_username, panel_password, token) as api:
            await api.disable_user(username)
    elif ptype == "MARZBAN":
        async with MarzbanPanel(base_url, panel_username, panel_password, token) as api:
            await api.disable_user(username)
    elif ptype in ("PASARGUARD", "PASURGARD", "PASARGAD"):
        async with PasarGuardPanel(base_url, api_key=token, username=panel_username, password=panel_password) as api:
            await api.disable_user(username)
