# 메이원헤어 체크인 백엔드

아이패드(HTML) → 이 서버 → 알리고 SMS → 디자이너 폰

## 배포

Railway에 자동 배포. GitHub 연동.

## 환경변수 (Railway에 입력)

- `ALIGO_API_KEY`: 알리고 API 키
- `ALIGO_USER_ID`: 알리고 가입 아이디
- `ALIGO_SENDER`: 등록한 발신번호 (예: 01012345678)
- `ALIGO_TEST_MODE`: N (실제 발송) / Y (테스트)

## API

- `GET /` - 서버 상태
- `GET /health` - 헬스체크
- `POST /sms/send` - SMS 발송
- `GET /sms/balance` - 잔액 조회

## 로컬 테스트

```bash
pip install -r requirements.txt
cp .env.example .env  # 그리고 실제 값 입력
uvicorn main:app --reload
```
