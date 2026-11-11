"""
Zarinpal v4 Payment Gateway
Amount is in Tomans in our bot → converted to Rials (*10) for API.
"""
from __future__ import annotations
import httpx
from typing import Any
import logging

logger = logging.getLogger(__name__)

PROD_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
PROD_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
PROD_START = "https://www.zarinpal.com/pg/StartPay/{authority}"

SANDBOX_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
SANDBOX_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
SANDBOX_START = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"


class ZarinpalError(Exception):
    def __init__(self, message: str, code: int | None = None, detail: Any = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)


class Zarinpal:
    def __init__(self, merchant_id: str, sandbox: bool = False, callback_url: str = "https://t.me/"):
        self.merchant_id = merchant_id
        self.sandbox = sandbox
        self.callback_url = callback_url

    @property
    def request_url(self) -> str:
        return SANDBOX_REQUEST if self.sandbox else PROD_REQUEST

    @property
    def verify_url(self) -> str:
        return SANDBOX_VERIFY if self.sandbox else PROD_VERIFY

    def start_pay_url(self, authority: str) -> str:
        tmpl = SANDBOX_START if self.sandbox else PROD_START
        return tmpl.format(authority=authority)

    async def request_payment(
        self,
        amount_toman: int,
        description: str,
        callback_url: str | None = None,
        mobile: str | None = None,
        email: str | None = None,
    ) -> dict:
        """
        Returns dict with authority and payment_url.
        amount_toman is converted to Rials.
        """
        amount_rial = int(amount_toman) * 10
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_rial,
            "description": description[:255],
            "callback_url": callback_url or self.callback_url,
        }
        metadata = {}
        if mobile:
            metadata["mobile"] = mobile
        if email:
            metadata["email"] = email
        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.request_url, json=payload)
            data = resp.json()

        # v4 response: {"data": {"code": 100, "authority": "...", ...}, "errors": []}
        if isinstance(data, dict) and "data" in data:
            inner = data["data"] or {}
            code = inner.get("code")
            if code == 100:
                authority = inner.get("authority")
                return {
                    "ok": True,
                    "authority": authority,
                    "payment_url": self.start_pay_url(authority),
                    "fee": inner.get("fee"),
                    "raw": data,
                }
            raise ZarinpalError(
                f"Zarinpal request failed code={code}",
                code=code,
                detail=data,
            )
        raise ZarinpalError("Unexpected Zarinpal response", detail=data)

    async def verify_payment(self, amount_toman: int, authority: str) -> dict:
        amount_rial = int(amount_toman) * 10
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_rial,
            "authority": authority,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.verify_url, json=payload)
            data = resp.json()

        if isinstance(data, dict) and "data" in data:
            inner = data["data"] or {}
            code = inner.get("code")
            # 100 = success, 101 = already verified
            if code in (100, 101):
                return {
                    "ok": True,
                    "code": code,
                    "ref_id": inner.get("ref_id"),
                    "card_pan": inner.get("card_pan"),
                    "raw": data,
                }
            raise ZarinpalError(
                f"Verify failed code={code}",
                code=code,
                detail=data,
            )
        raise ZarinpalError("Unexpected verify response", detail=data)

    async def test_merchant(self) -> dict:
        """Small sandbox-friendly connectivity test (1 Toman request)."""
        try:
            # Use minimal amount; may fail on production merchant without sandbox
            result = await self.request_payment(
                amount_toman=1000,
                description="ROBIXA connection test",
                callback_url=self.callback_url,
            )
            return {"ok": True, "authority": result.get("authority")}
        except ZarinpalError as e:
            # Code 100-ish means merchant accepted; other codes still prove reachability
            return {"ok": False, "error": e.message, "code": e.code, "detail": e.detail}
        except Exception as e:
            return {"ok": False, "error": str(e)}
