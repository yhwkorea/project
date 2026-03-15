# checklist.md — 스마트 교통 알람 구현 체크리스트

**작성일**: 2026-03-15
**작성자**: threat-modeler
**기반**: DFD Level 1 + STRIDE 위협 분석
**상태**: 초안

---

## 체크리스트

### [설정 관리 — FR-001~006]

- [x] DONE: FR-001 출발지 설정 UI — GPS 현재 위치 취득 (FusedLocationProvider) 및 주소 검색 기능 구현
- [x] DONE: FR-001 위치 권한 요청 흐름 구현 (ACCESS_FINE_LOCATION, 거부 시 주소 검색 폴백)
- [~] IN_PROGRESS: FR-002 목적지 등록 화면 구현 (단일 목적지 텍스트 입력 구현됨, 지도 핀·최대 5개 미구현)
- [x] DONE: FR-003 목적지별 도착 목표 시각 설정 UI 구현 (TimePicker — 시/분 드롭다운)
- [x] DONE: FR-004 준비 시간 슬라이더 구현 (10~90분, 기본값 30분)
- [x] DONE: FR-005 모니터링 시작 시각 설정 UI 구현
- [x] DONE: FR-006 요일별 알람 활성화/비활성화 토글 UI 구현
- [~] IN_PROGRESS: FR-001~006 설정 데이터 Room DB AlarmProfile 테이블에 저장 (암호화 미적용)

### [경로 계산 — FR-010~015]

- [x] DONE: FR-010 ODsay Lab API 대중교통 경로 계산 구현 (버스+지하철+도보 복합)
- [ ] TODO: FR-010 ODsay API 호출 일일 한도(1,000회) 모니터링 및 초과 시 Tmap 보조 API 폴백 로직 구현
- [x] DONE: FR-011 환승 정보 파싱 및 표시 (환승 횟수 포함, 환승 대기 시간 미구현)
- [x] DONE: FR-012 도보 구간 거리·소요 시간 경로 계산에 포함
- [x] DONE: FR-013 이동수단별 경로 탭 UI — 도보/버스/지하철/버스+지하철 4가지 탭, 각 탭 총 이동시간 표시, 사용자가 선택한 경로 기준으로 알람 설정
- [x] DONE: FR-014 D2D 총 소요 시간 계산 로직 구현 (준비시간 + 도보 + 대기 + 이동)
- [x] DONE: FR-015 실시간 소요 시간 N분 간격 재계산 WorkManager PeriodicWork 구현 (TrafficMonitorWorker)
- [x] DONE: FR-016 경로 지도 보기 — "지도 보기" 버튼 → Google Maps WebView (출발지→목적지 대중교통 경로)
- [x] DONE: FR-017 새벽 운행 중단 안내 — ODsay 에러 코드(-8, -98) 시 "이 시간대에 운행하는 대중교통이 없어요" 메시지

### [실시간 교통 정보 — FR-020~023]

- [~] IN_PROGRESS: FR-020 ODsay Lab API 버스 실시간 도착 정보 조회 (API 연동 코드 있으나 openapi.seoul.go.kr:8088 ERROR-500 응답 중)
- [!] FAILED: FR-020 서울열린데이터광장 버스 실시간 API — openapi.seoul.go.kr:8088 KEY 오류, ws.bus.go.kr는 data.go.kr 별도 키 필요
- [~] IN_PROGRESS: FR-021 서울열린데이터광장 지하철 실시간 운행 정보 조회 (swopenAPI.seoul.go.kr 연동 코드 구현, 키 유효 확인됨)
- [ ] TODO: FR-022 교통 정체 정보 조회 및 도보 경로 우회 반영 (SHOULD)
- [ ] TODO: FR-023 기상청 단기예보 API + 초단기실황 API 연동 구현
- [ ] TODO: FR-023 강수량(mm) 단계별 계수 적용 로직 구현
  - 0mm: 계수 1.0 (기본)
  - 1~4mm: 계수 1.05 (+5%)
  - 5~9mm: 계수 1.15 (+15%)
  - 10mm+: 계수 1.25 (+25%)
- [ ] TODO: FR-023 우천 계수 사용자 앱 설정에서 조정 가능한 UI 구현

### [알림 시스템 — FR-030~036]

- [x] DONE: FR-030 기상 알람 로컬 알림 구현 (AlarmManager.setExactAndAllowWhileIdle + RingtoneManager.TYPE_ALARM + FLAG_INSISTENT)
- [ ] TODO: FR-030 SCHEDULE_EXACT_ALARM 권한 런타임 요청 흐름 구현 (Android 12+)
- [x] DONE: FR-031 교통 상황 변화 감지 시 재알림 발송 로직 구현 (TrafficMonitorWorker → AlarmScheduler.reschedule)
- [ ] TODO: FR-032 재알림에 변경된 출발 시각 + 변경 원인 텍스트 포함
- [ ] TODO: FR-033 전날 밤 우천 예보 사전 알림 구현 (SHOULD)
- [ ] TODO: FR-034 최적 출발 시각 경과 경고 알림 구현 (SHOULD)
- [ ] TODO: FR-035 알림음·진동·팝업 커스터마이징 설정 UI (COULD)
- [ ] TODO: FR-036 스누즈 후 재계산 재알림 구현 (SHOULD)
- [x] DONE: FCM 미사용 확인 — 모든 알림이 로컬(WorkManager + AlarmManager)로 구현됨

### [대안 경로 제안 — FR-040~042]

- [ ] TODO: FR-040 현재 경로 지연/장애 감지 시 대안 경로 자동 계산 및 알림 발송
- [ ] TODO: FR-041 대안 경로 vs 원래 경로 예상 도착 시각 차이 표시 UI
- [ ] TODO: FR-042 사용자가 대안 경로 선택 시 모니터링 경로 전환 로직 (SHOULD)

### [GPS 도착 감지 — TBD-006 결정]

- [ ] TODO: 목적지 Geofencing 설정 (FusedLocationProvider Geofence API, 반경 200m 기본)
- [ ] TODO: 목적지 반경 진입 후 체류 감지 시 자동 도착 기록 로직 구현
- [ ] TODO: 도착 기록 Room DB 저장 (FR-051 예측 오차 계산용)
- [ ] TODO: Geofencing 백그라운드 동작 Doze 모드 대응 검증

### [히스토리 및 분석 — FR-050~051]

- [ ] TODO: FR-050 최근 30일 D2D 소요 시간 이력 저장 및 요일별 평균 표시 UI (COULD)
- [ ] TODO: FR-051 예측 도착 vs 실제 도착 오차 기록 및 알고리즘 보정 반영 (COULD)

### [백그라운드 · 배터리 — NFR-010~022]

- [ ] TODO: NFR-010 외부 API 응답 실패 시 Room 캐시 폴백 + "실시간 정보 없음" 표시 구현
- [ ] TODO: NFR-011 오프라인 상태에서 마지막 계산 알람 유지 로직 확인
- [ ] TODO: NFR-012 WorkManager 자동 재시작 설정 (setRequiredNetworkType + RETRY 정책)
- [x] DONE: NFR-013 알람 정확도 ±1분 이내 — AlarmManager.setExactAndAllowWhileIdle 사용
- [ ] TODO: NFR-020 Doze 모드 대응 — WorkManager Constraints + setRequiresCharging/Idle 조건 설정
- [ ] TODO: NFR-021 모니터링 비활성화 시간대 네트워크 요청 중단 로직 구현
- [ ] TODO: NFR-022 응답 캐싱 전략 구현 (OkHttp Cache + Room 캐시, 캐시 TTL 5분)

---

## 보안 체크리스트 (STRIDE 기반)

### Spoofing (사칭)

- [x] DONE: SEC-S01 ODsay API 키 앱 번들에 평문 하드코딩 금지 — local.properties → BuildConfig로 주입
- [x] DONE: SEC-S02 서울열린데이터광장, 기상청 API 키 동일 기준 적용 (local.properties → BuildConfig)
- [ ] SEC-S03 API 응답 출처 검증 — HTTPS 전용 통신, 인증서 핀닝 고려 (MVP 이후)

### Tampering (변조)

- [ ] SEC-T01 Room DB 저장 시 위치 정보 암호화 (SQLCipher 또는 EncryptedSharedPreferences) (NFR-040)
- [ ] SEC-T02 WorkManager 작업 파라미터 외부 입력 검증 — 사용자 입력값 경계 검사
- [ ] SEC-T03 API 응답 데이터 파싱 시 예외 처리 및 유효성 검증 (kotlinx.serialization + try-catch)

### Repudiation (부인)

- [ ] SEC-R01 알람 발송 이력 로컬 로그 기록 (디버그/분석용, 개인정보 미포함)
- [ ] SEC-R02 Geofencing 도착 감지 이벤트 타임스탬프 기록

### Information Disclosure (정보 유출)

- [ ] SEC-I01 API 오류 메시지에 API 키, 좌표 원문 노출 금지 — 로그 레벨 조정
- [ ] SEC-I02 위치 정보를 서버로 전송하지 않음 확인 (API 호출 시 좌표만, 최소화) (NFR-040)
- [ ] SEC-I03 앱 내 개인정보 처리방침 화면 구현 (NFR-043)
- [ ] SEC-I04 ProGuard/R8 난독화 설정으로 API 키 역공학 방지 (NFR-041)

### Denial of Service (서비스 거부)

- [ ] SEC-D01 ODsay API 일 1,000회 한도 관리 — 호출 횟수 카운터 구현 + 한도 초과 시 Tmap 폴백
- [ ] SEC-D02 WorkManager 재시도 횟수 상한 설정 (무한 재시도 방지)
- [ ] TODO: SEC-D03 네트워크 타임아웃 설정 (OkHttp: connect 10s, read 15s)
- [ ] SEC-D04 Geofencing 과도한 위치 업데이트 방지 — 최소 업데이트 간격 설정

### Elevation of Privilege (권한 상승)

- [ ] SEC-E01 권한 최소화 — ACCESS_FINE_LOCATION, SCHEDULE_EXACT_ALARM 외 불필요 권한 미선언
- [ ] SEC-E02 위치 권한 Runtime Permission — 거부 시 앱 동작 축소 모드(주소 입력 폴백) 구현
- [ ] SEC-E03 exported=false 설정 — BroadcastReceiver, Service 컴포넌트 외부 노출 방지

---

## 진행 상태 범례

```
- [ ] TODO        : 미시작
- [~] IN_PROGRESS : 진행 중
- [x] DONE        : 완료
- [!] FAILED      : 실패 (재작업 필요)
```

---

*verification-analyst는 구현 완료 항목을 DONE으로, 실패 항목을 FAILED로 업데이트할 것.*
*전체 DONE → release-reviewer 투입*
