"""
메이원헤어 / 모모제인 체크인 백엔드
- 아이패드(HTML)에서 체크인 → 이 서버 호출 → 알리고 SMS 발송 → 디자이너 폰
- 매장(salon)별로 다른 알리고 계정 사용
"""
import os
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ================== 매장별 알리고 설정 ==================
ALIGO_API_KEY = os.getenv("ALIGO_API_KEY", "")
ALIGO_USER_ID = os.getenv("ALIGO_USER_ID", "")
ALIGO_SENDER = os.getenv("ALIGO_SENDER", "")
ALIGO_TEST_MODE = os.getenv("ALIGO_TEST_MODE", "N")

MOMOZAIN_ALIGO_API_KEY = os.getenv("MOMOZAIN_ALIGO_API_KEY", "")
MOMOZAIN_ALIGO_USER_ID = os.getenv("MOMOZAIN_ALIGO_USER_ID", "")
MOMOZAIN_ALIGO_SENDER = os.getenv("MOMOZAIN_ALIGO_SENDER", "")

ALIGO_SEND_URL = "https://apis.aligo.in/send/"


def get_salon_config(salon: str) -> dict:
    if salon and salon.lower() == "momozain":
        return {
            "api_key": MOMOZAIN_ALIGO_API_KEY,
            "user_id": MOMOZAIN_ALIGO_USER_ID,
            "sender": MOMOZAIN_ALIGO_SENDER,
            "test_mode": ALIGO_TEST_MODE,
            "name": "모모제인",
        }
    return {
        "api_key": ALIGO_API_KEY,
        "user_id": ALIGO_USER_ID,
        "sender": ALIGO_SENDER,
        "test_mode": ALIGO_TEST_MODE,
        "name": "메이원",
    }


app = FastAPI(
    title="체크인 SMS API (메이원 / 모모제인)",
    version="2.0.0",
    description="아이패드 체크인 → 매장별 알리고로 디자이너 폰에 SMS 발송"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SMSRequest(BaseModel):
    receiver: str
    message: str
    salon: str | None = None


class SMSResponse(BaseModel):
    success: bool
    message: str
    aligo_response: dict | None = None


@app.get("/")
def root():
    return {
        "service": "체크인 SMS API (메이원 / 모모제인)",
        "status": "running",
        "config": {
            "mayone_configured": bool(ALIGO_API_KEY and ALIGO_USER_ID and ALIGO_SENDER),
            "momozain_configured": bool(MOMOZAIN_ALIGO_API_KEY and MOMOZAIN_ALIGO_USER_ID and MOMOZAIN_ALIGO_SENDER),
            "test_mode": ALIGO_TEST_MODE == "Y",
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/my-ip")
def my_ip():
    return {"ip": requests.get("https://api.ipify.org").text}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/sms/send", response_model=SMSResponse)
def send_sms(payload: SMSRequest):
    cfg = get_salon_config(payload.salon)

    if not cfg["api_key"] or not cfg["user_id"] or not cfg["sender"]:
        raise HTTPException(
            status_code=500,
            detail=f"[{cfg['name']}] 알리고 API 설정이 누락되었습니다. 환경변수 확인 필요"
        )

    receiver_clean = payload.receiver.replace("-", "").replace(" ", "")

    if not receiver_clean.isdigit() or len(receiver_clean) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 수신번호: {payload.receiver}"
        )

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다")

    sender_clean = cfg["sender"].replace("-", "").replace(" ", "")

    try:
        resp = requests.post(
            ALIGO_SEND_URL,
            data={
                "key": cfg["api_key"],
                "user_id": cfg["user_id"],
                "sender": sender_clean,
                "receiver": receiver_clean,
                "msg": payload.message,
                "msg_type": "LMS" if len(payload.message) > 90 else "SMS",
                "testmode_yn": cfg["test_mode"],
            },
            timeout=10,
        )
        result = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"알리고 서버 통신 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMS 발송 오류: {str(e)}")

    result_code = str(result.get("result_code", ""))

    if result_code == "1":
        return SMSResponse(
            success=True,
            message=f"[{cfg['name']}] SMS 발송 성공",
            aligo_response=result,
        )
    else:
        error_msg = result.get("message", "알 수 없는 오류")
        return SMSResponse(
            success=False,
            message=f"[{cfg['name']}] 알리고 발송 실패: {error_msg}",
            aligo_response=result,
        )


@app.get("/sms/balance")
def get_balance(salon: str | None = None):
    cfg = get_salon_config(salon)

    if not cfg["api_key"] or not cfg["user_id"]:
        raise HTTPException(status_code=500, detail=f"[{cfg['name']}] 알리고 API 설정 누락")

    try:
        resp = requests.post(
            "https://apis.aligo.in/remain/",
            data={"key": cfg["api_key"], "user_id": cfg["user_id"]},
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
