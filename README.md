# sms-serial-redis (com.nasa)

Project đọc SMS OTP từ nhiều modem GSM/4G qua Serial (AT command) và push lên Redis.
Tổ chức package kiểu Java: `com.nasa.*`

## Tính năng
- Không bắt buộc `SERIAL_PORTS`
- PortManager scan serial ports, probe modem bằng `AT` + `AT+CGSN/AT+GSN` lấy IMEI
- Mỗi IMEI có 1 worker đọc SMS
- Modem rớt/cắm lại (COM đổi) -> worker tự dừng, PortManager spawn lại theo IMEI
- Parse OTP bằng regex và push Redis (TTL 300s mặc định)

## Cấu hình
Copy `.env.example` -> `.env` và chỉnh tối thiểu:
- `REDIS_URL=redis://localhost:6379/0`

Tuỳ chọn:
- `SERIAL_PORTS=COM5,COM6` (nếu muốn chỉ scan một số port)
- `BAUDRATE=115200`
- `SCAN_INTERVAL_SECONDS=3.0`
- `PROBE_TIMEOUT_SECONDS=1.2`
- `SERIAL_TIMEOUT_SECONDS=2.0`
- `POLL_INTERVAL_SECONDS=2.0`
- `OTP_REGEX=\b(\d{4,8})\b`
- `OTP_TTL_SECONDS=300`
- `OTP_KEY_PREFIX=otp:`
- `DELETE_AFTER_READ=true`
- `LOG_LEVEL=INFO`

## Chạy
```bash
pip install -r requirements.txt
python -m com.nasa.app.main
```

## Redis key/value
- Key: `{OTP_KEY_PREFIX}{sender}`
- Value: JSON: `{"otp":"123456","sender":"+8498...","text":"...","received_at":"...","port":"COM5","imei":"...","index":12}`
