"""
메이원헤어 체크인 백엔드
- 아이패드(HTML)에서 체크인 → 이 서버 호출 → 알리고 SMS 발송 → 디자이너 폰
"""
import os
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ================== 설정 ==================
ALIGO_API_KEY = os.getenv("ALIGO_API_KEY", "")
ALIGO_USER_ID = os.getenv("ALIGO_USER_ID", "")
ALIGO_SENDER = os.getenv("ALIGO_SENDER", "")  # 발신번호
ALIGO_TEST_MODE = os.getenv("ALIGO_TEST_MODE", "N")  # 'Y'로 두면 실제 발송 안 됨

ALIGO_SEND_URL = "https://apis.aligo.in/send/"

# ================== FastAPI ==================
app = FastAPI(
    title="메이원헤어 체크인 API",
    version="1.0.0",
    description="아이패드 체크인 → 디자이너 폰으로 SMS 발송"
)

# CORS - 모든 출처 허용 (Netlify URL이 변경될 수 있어서)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================== 모델 ==================
class SMSRequest(BaseModel):
    receiver: str   # 받는 사람 폰번호 (디자이너 폰)
    message: str    # SMS 내용


class SMSResponse(BaseModel):
    success: bool
    message: str
    aligo_response: dict | None = None


# ================== 엔드포인트 ==================
@app.get("/")
def root():
    """서버 상태 확인용"""
    return {
        "service": "메이원헤어 체크인 API",
        "status": "running",
        "config": {
            "aligo_configured": bool(ALIGO_API_KEY and ALIGO_USER_ID and ALIGO_SENDER),
            "test_mode": ALIGO_TEST_MODE == "Y",
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/my-ip")
def my_ip():
    return {"ip": requests.get("https://api.ipify.org").text}


@app.get("/health")
def health():
    """Railway 헬스체크용"""
    return {"ok": True}


@app.post("/sms/send", response_model=SMSResponse)
def send_sms(payload: SMSRequest):
    """
    SMS 발송 엔드포인트
    HTML이 체크인 시 이 함수 호출 → 알리고 API 호출 → 디자이너 폰으로 SMS
    """
    # 환경변수 검증
    if not ALIGO_API_KEY or not ALIGO_USER_ID or not ALIGO_SENDER:
        raise HTTPException(
            status_code=500,
            detail="알리고 API 설정이 누락되었습니다. 환경변수 확인 필요"
        )

    # 받는 번호 정규화 (하이픈 제거)
    receiver_clean = payload.receiver.replace("-", "").replace(" ", "")

    # 검증
    if not receiver_clean.isdigit() or len(receiver_clean) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 수신번호: {payload.receiver}"
        )

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다")

    # 알리고 API 호출
    sender_clean = ALIGO_SENDER.replace("-", "").replace(" ", "")
    
    try:
        resp = requests.post(
            ALIGO_SEND_URL,
            data={
                "key": ALIGO_API_KEY,
                "user_id": ALIGO_USER_ID,
                "sender": sender_clean,
                "receiver": receiver_clean,
                "msg": payload.message,
                "msg_type": "LMS" if len(payload.message) > 90 else "SMS",
                "testmode_yn": ALIGO_TEST_MODE,
            },
            timeout=10,
        )
        result = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"알리고 서버 통신 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMS 발송 오류: {str(e)}")

    # 알리고 응답 처리
    # 알리고 응답: {"result_code": "1", "message": "success", ...}
    # result_code: "1" 이면 성공, 음수이면 에러
    result_code = str(result.get("result_code", ""))

    if result_code == "1":
        return SMSResponse(
            success=True,
            message="SMS 발송 성공",
            aligo_response=result,
        )
    else:
        # 발송 실패
        error_msg = result.get("message", "알 수 없는 오류")
        return SMSResponse(
            success=False,
            message=f"알리고 발송 실패: {error_msg}",
            aligo_response=result,
        )


@app.get("/sms/balance")
def get_balance():
    """알리고 잔액 조회 (선택 기능)"""
    if not ALIGO_API_KEY or not ALIGO_USER_ID:
        raise HTTPException(status_code=500, detail="알리고 API 설정 누락")

    try:
        resp = requests.post(
            "https://apis.aligo.in/remain/",
            data={"key": ALIGO_API_KEY, "user_id": ALIGO_USER_ID},
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
