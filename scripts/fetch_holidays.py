#!/usr/bin/env python3
"""한국 공휴일(대체·임시공휴일, 선거일 포함)을 한국천문연구원 특일정보 API에서 받아 holidays.json으로 남긴다.

- 환율 작업(rates.yml) 안에서 주 1회(월요일)만 돈다. 올해·내년 2년 × 12달 = 24번 호출(일일 한도 안).
- 키는 GitHub Secret KASI_SERVICE_KEY(공공데이터포털 일반 인증키 Decoding 값)에서만 읽고, 어디에도 출력하지 않는다.
- 키가 없으면 아무것도 하지 않고 끝난다(작업은 실패하지 않음).
- 한 해라도 비거나 실패하면 그 해는 전에 받은 값을 그대로 둔다. 전부 실패하면 파일을 바꾸지 않는다.
앱은 이 파일만 받는다(API를 직접 부르지 않음).
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

OUT = "holidays.json"
KST = datetime.timezone(datetime.timedelta(hours=9))
ENDPOINT = "https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"


def fetch_month(key, year, month):
    # 키가 들어간 주소는 오류 메시지에도 남기지 않는다
    query = urllib.parse.urlencode({"serviceKey": key, "solYear": year, "solMonth": f"{month:02d}", "_type": "json", "numOfRows": 50})
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": "supervivo-rates/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read())
    header = body.get("response", {}).get("header", {})
    if header.get("resultCode") not in ("00", "0000", None):
        raise RuntimeError(f"resultCode {header.get('resultCode')}")
    items = body.get("response", {}).get("body", {}).get("items") or {}
    item = items.get("item", []) if isinstance(items, dict) else []
    return item if isinstance(item, list) else [item]


def fetch_year(key, year):
    days = {}
    for month in range(1, 13):
        for entry in fetch_month(key, year, month):
            if entry.get("isHoliday") != "Y":
                continue
            raw = str(entry["locdate"])
            days.setdefault(f"{raw[:4]}-{raw[4:6]}-{raw[6:]}", []).append(entry.get("dateName", ""))
    return days


def main():
    key = os.environ.get("KASI_SERVICE_KEY", "").strip()
    if not key:
        print("KASI_SERVICE_KEY가 없어 공휴일 갱신을 건너뛴다")
        return
    now = datetime.datetime.now(KST)
    previous = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            previous = json.load(f).get("years", {})
    years = dict(previous)
    updated = []
    for year in (now.year, now.year + 1):
        try:
            days = fetch_year(key, year)
        except Exception as error:
            print(f"{year} 받기 실패({type(error).__name__}) — 전에 받은 값 유지", file=sys.stderr)
            continue
        if not days:
            print(f"{year} 결과가 비어 전에 받은 값 유지", file=sys.stderr)
            continue
        years[str(year)] = dict(sorted(days.items()))
        updated.append(year)
    if not updated:
        print("새로 받은 해가 없어 holidays.json을 그대로 둔다")
        return
    out = {
        "source": "한국천문연구원 특일정보(공공데이터포털)",
        "updatedAt": now.isoformat(timespec="seconds"),
        "years": dict(sorted(years.items())),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"공휴일 갱신: {updated}")


if __name__ == "__main__":
    main()
