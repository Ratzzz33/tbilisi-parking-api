#!/usr/bin/env bash
# Silent on success. Emits a Telegram-ready alert on a failed health check
# or when the wallet balance is below the configured threshold.
set -euo pipefail

API_URL="${PARKING_API_URL:-http://127.0.0.1:8127/health}"
THRESHOLD_GEL="${BALANCE_ALERT_THRESHOLD_GEL:-10}"

response=""
if ! response=$(curl --fail --silent --show-error --max-time 15 "$API_URL" 2>&1); then
  service_state=$(systemctl is-active tbilisi-parking-api 2>/dev/null || true)
  printf '🚨 Parking API недоступен\nСервис systemd: %s\nПроверка: %s\nВремя UTC: %s\n' \
    "${service_state:-unknown}" "$API_URL" "$(date -u '+%Y-%m-%d %H:%M:%S')"
  exit 0
fi

PAYLOAD_JSON="$response" python3 - "$THRESHOLD_GEL" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

threshold = float(sys.argv[1])
try:
    payload = json.loads(os.environ["PAYLOAD_JSON"])
    if payload.get("status") != "ok":
        raise ValueError(f"API status: {payload.get('status', 'unknown')}")
    balance = float(payload["person"]["balanceAmount"])
except Exception as exc:
    state = "unknown"
    try:
        import subprocess
        state = subprocess.check_output(
            ["systemctl", "is-active", "tbilisi-parking-api"], text=True
        ).strip()
    except Exception:
        pass
    print(
        "🚨 Parking API вернул некорректный ответ\n"
        f"Сервис systemd: {state}\n"
        f"Причина: {exc}\n"
        f"Время UTC: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}"
    )
    sys.exit(0)

if balance < threshold:
    print(
        "⚠️ Низкий баланс Parking Tbilisi\n"
        f"Баланс: {balance:.2f} GEL (порог: {threshold:.2f} GEL)\n"
        "Проверяется каждые 5 минут; это уведомление будет повторяться, пока баланс ниже порога."
    )
PY
