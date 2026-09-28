import os
import re

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="MSG91 Render Test")

MSG91_URL = "https://control.msg91.com/api/v5/widget/sendOtp"


class OTPRequest(BaseModel):
    mobile: str


@app.get("/")
def health():
    return {"status": "ok", "service": "msg91-render-test"}


@app.post("/test-otp")
def test_otp(
    payload: OTPRequest,
    x_test_key: str | None = Header(default=None),
):
    test_key = os.getenv("TEST_API_KEY", "")
    if not test_key or x_test_key != test_key:
        raise HTTPException(403, "Unauthorized")

    mobile = payload.mobile.strip()

    if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
        raise HTTPException(400, "Enter a valid Indian mobile number")

    authkey = os.getenv("MSG91_AUTHKEY", "").strip()
    widget_id = os.getenv("MSG91_WIDGET_ID", "").strip()

    if not authkey or not widget_id:
        raise HTTPException(503, "MSG91 configuration missing")

    try:
        response = httpx.post(
            MSG91_URL,
            headers={
                "authkey": authkey,
                "Content-Type": "application/json",
            },
            json={
                "widgetId": widget_id,
                "identifier": "91" + mobile,
            },
            timeout=15.0,
            follow_redirects=False,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        # Never return the OTP request ID or provider tokens.
        return {
            "http_status": response.status_code,
            "provider_type": result.get("type") if isinstance(result, dict) else None,
            "provider_message": (
                "redacted"
                if response.is_success
                else result.get("message", "No JSON error message")
                if isinstance(result, dict)
                else "No JSON error message"
            ),
            "server": response.headers.get("server"),
            "cf_ray": response.headers.get("cf-ray"),
        }

    except httpx.RequestError:
        raise HTTPException(502, "Network request to MSG91 failed")

@app.post("/test-otp-gateway")
def test_otp_gateway(
    payload: OTPRequest,
    x_test_key: str | None = Header(default=None),
):
    test_key = os.getenv("TEST_API_KEY", "")
    if not test_key or x_test_key != test_key:
        raise HTTPException(403, "Unauthorized")

    mobile = payload.mobile.strip()

    if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
        raise HTTPException(400, "Enter a valid Indian mobile number")

    gateway_url = os.getenv("MSG91_GATEWAY_URL", "").strip().rstrip("/")
    gateway_key = os.getenv("MSG91_GATEWAY_KEY", "").strip()

    if not gateway_url or not gateway_key:
        raise HTTPException(503, "Gateway configuration missing")

    try:
        response = httpx.post(
            gateway_url + "/test-otp",
            headers={
                "x-gateway-key": gateway_key,
                "Content-Type": "application/json",
            },
            json={
                "mobile": mobile,
            },
            timeout=20.0,
            follow_redirects=False,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        return {
            "gateway_http_status": response.status_code,
            "msg91_http_status": (
                result.get("http_status")
                if isinstance(result, dict)
                else None
            ),
            "provider_type": (
                result.get("provider_type")
                if isinstance(result, dict)
                else None
            ),
            "provider_message": (
                result.get("provider_message")
                if isinstance(result, dict)
                else "Invalid gateway response"
            ),
        }

    except httpx.RequestError:
        raise HTTPException(502, "Network request to gateway failed")