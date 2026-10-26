"""한국수출입은행 환율을 받아 rates.json과 history/날짜.json으로 저장한다.

- 인증키는 환경 변수 KEXIM_AUTHKEY에서만 읽고 어디에도 출력하지 않는다.
- 키가 없으면 아무것도 바꾸지 않고 끝낸다(실패로 보지 않는다).
- 비영업일·오전 11시 전이라 빈 응답이면 이전 파일을 그대로 둔다.
- history/에는 최근 60일 치를 남긴다(카드사 전표 접수일 환율을 찾을 때 쓴다).
- rates.json의 date는 환율 고시일, checkedAt은 마지막으로 확인한 때(새 환율이 없어도 매번 남김)다.
"""
import datetime
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

API = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
ROOT = pathlib.Path(__file__).resolve().parent.parent
KST = datetime.timezone(datetime.timedelta(hours=9))


def number(text):
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return None


def fetch(key, day):
    query = urllib.parse.urlencode({"authkey": key, "searchdate": day.strftime("%Y%m%d"), "data": "AP01"})
    with urllib.request.urlopen(f"{API}?{query}", timeout=30) as response:
        return json.load(response)


def parse(items, day):
    rates = {}
    for item in items:
        if item.get("result") != 1:
            continue
        unit_text = item.get("cur_unit", "")
        code = unit_text.split("(")[0].strip()
        # JPY(100), IDR(100)처럼 100단위로 고시하는 통화
        unit = 100 if "(100)" in unit_text else 1
        tts, deal, ttb = number(item.get("tts")), number(item.get("deal_bas_r")), number(item.get("ttb"))
        if code == "KRW" or not tts or not deal:
            continue
        rates[code] = {"name": item.get("cur_nm", ""), "unit": unit, "tts": tts, "ttb": ttb, "deal": deal}
    return {
        "source": "한국수출입은행 현재환율(AP01)",
        "date": day.isoformat(),
        "fetchedAt": now_utc(),
        "rates": dict(sorted(rates.items())),
    }


KEEP_DAYS = 60


def prune_history(today):
    """접수일 환율을 찾을 수 있게 최근 60일 치만 남긴다"""
    oldest = today - datetime.timedelta(days=KEEP_DAYS)
    for path in (ROOT / "history").glob("*.json"):
        try:
            if datetime.date.fromisoformat(path.stem) < oldest:
                path.unlink()
        except ValueError:
            continue


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mark_checked():
    """새 환율이 없어도(휴일·갱신 전·오류) 확인한 때(checkedAt)만 남긴다. 앱은 이것으로 '확인은 했는데 휴일'과 '확인이 멈춤'을 가린다"""
    path = ROOT / "rates.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["checkedAt"] = now_utc()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    key = os.environ.get("KEXIM_AUTHKEY", "").strip()
    if not key:
        print("KEXIM_AUTHKEY가 없어 건너뜀")
        return 0
    day = datetime.datetime.now(KST).date()
    try:
        items = fetch(key, day)
    except Exception as error:  # 네트워크 오류: 이전 파일 유지
        print(f"받지 못함({type(error).__name__}), 이전 파일 유지")
        mark_checked()
        return 0
    if not isinstance(items, list) or not items:
        print("빈 응답(비영업일 또는 갱신 전), 이전 파일 유지")
        mark_checked()
        return 0
    data = parse(items, day)
    if not data["rates"]:
        print("쓸 수 있는 환율이 없어 이전 파일 유지")
        mark_checked()
        return 0
    text = json.dumps({**data, "checkedAt": now_utc()}, ensure_ascii=False, indent=1) + "\n"
    (ROOT / "rates.json").write_text(text, encoding="utf-8")
    (ROOT / "history").mkdir(exist_ok=True)
    (ROOT / "history" / f"{day.isoformat()}.json").write_text(text, encoding="utf-8")
    prune_history(day)
    print(f"{day.isoformat()} 환율 {len(data['rates'])}개 저장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
