# supervivo-rates

Supervivo(적자생존) 앱이 해외 결제의 예상 원화 금액을 셀 때 쓰는 환율 파일입니다.

- `rates.json`: 가장 최근 영업일의 한국수출입은행 현재환율(전신환매도율 `tts`, 매매기준율 `deal`, 전신환매입률 `ttb`). `unit`이 100이면 100단위 고시(JPY, IDR).
- `history/YYYY-MM-DD.json`: 날짜별 같은 형식, 최근 60일 치.
- GitHub Actions가 영업일 11:30·12:30(KST)에 갱신합니다. 인증키는 저장소 Secret `KEXIM_AUTHKEY`에만 있고, 이 저장소의 파일에는 없습니다.
- 출처: 한국수출입은행 Open API. 참고용 값이며 카드사가 실제로 청구하는 금액과 다를 수 있습니다.
