# architecture.md — 스마트 교통 알람 설계 문서

**작성일**: 2026-03-15
**작성자**: threat-modeler
**기반**: requirements.md (CONFIRMED) + Clean Architecture + DFD Level 1

---

## 목차

1. [컴포넌트 구성 (Clean Architecture)](#1-컴포넌트-구성-clean-architecture)
2. [주요 데이터 흐름 (DFD Level 1)](#2-주요-데이터-흐름-dfd-level-1)
3. [외부 API 연동 구조](#3-외부-api-연동-구조)
4. [WorkManager 백그라운드 작업 설계](#4-workmanager-백그라운드-작업-설계)
5. [핵심 데이터 모델](#5-핵심-데이터-모델)
6. [보안 설계 결정](#6-보안-설계-결정)

---

## 1. 컴포넌트 구성 (Clean Architecture)

```
┌─────────────────────────────────────────────────────┐
│                  Presentation Layer                  │
│  ┌──────────────────┐   ┌─────────────────────────┐ │
│  │  Compose UI       │   │  ViewModel (StateFlow)  │ │
│  │  - OnboardingFlow │◄──│  - AlarmViewModel       │ │
│  │  - HomeScreen     │   │  - RouteViewModel       │ │
│  │  - RouteScreen    │   │  - SettingsViewModel    │ │
│  │  - SettingsScreen │   └────────────┬────────────┘ │
│  └──────────────────┘                │               │
└─────────────────────────────────────┼───────────────┘
                                       │ UseCase 호출
┌─────────────────────────────────────┼───────────────┐
│                  Domain Layer        │               │
│  ┌──────────────────────────────────▼─────────────┐ │
│  │                   UseCases                      │ │
│  │  - CalculateRouteUseCase                        │ │
│  │  - MonitorTrafficUseCase                        │ │
│  │  - ScheduleAlarmUseCase                         │ │
│  │  - DetectArrivalUseCase                         │ │
│  │  - ApplyWeatherCorrectionUseCase                │ │
│  └──────────────────────────────────┬─────────────┘ │
│  ┌──────────────────────────────────▼─────────────┐ │
│  │              Domain Models (순수 Kotlin)         │ │
│  │  AlarmProfile / Route / TransitInfo / Weather   │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────┼───────────────┘
                                       │ Repository 인터페이스
┌─────────────────────────────────────┼───────────────┐
│                   Data Layer         │               │
│  ┌──────────────────────────────────▼─────────────┐ │
│  │                 Repositories                    │ │
│  │  - AlarmRepository    - RouteRepository         │ │
│  │  - TrafficRepository  - WeatherRepository       │ │
│  │  - LocationRepository - HistoryRepository       │ │
│  └────────────┬──────────────────────┬────────────┘ │
│               │                      │               │
│  ┌────────────▼──────────┐ ┌─────────▼────────────┐ │
│  │    Remote DataSources  │ │  Local DataSources    │ │
│  │  - OdsayApiService     │ │  - AlarmDao (Room)    │ │
│  │  - TmapApiService      │ │  - RouteDao (Room)    │ │
│  │  - SeoulBusApiService  │ │  - HistoryDao (Room)  │ │
│  │  - SubwayApiService    │ │  - SettingsDataStore  │ │
│  │  - WeatherApiService   │ │                       │ │
│  └───────────────────────┘ └───────────────────────┘ │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │          Background Layer (WorkManager)        │   │
│  │  - TrafficMonitorWorker (5분/1분 주기)           │   │
│  │  - WeatherCheckWorker (3시간 주기)               │   │
│  │  - AlarmSchedulerWorker (정각 알람 예약)          │   │
│  │  - GeofencingManager (GPS 도착 감지)             │   │
│  └───────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

### 레이어별 의존 방향

```
Presentation → Domain ← Data
(Domain은 외부에 의존하지 않는 순수 비즈니스 로직)
```

---

## 2. 주요 데이터 흐름 (DFD Level 1)

```
┌─────────────┐
│   사용자     │
└──────┬──────┘
       │ 출발지/목적지/시각 설정
       ▼
┌─────────────────────────────────────────────────┐
│                  스마트 알람 앱                   │
│                                                  │
│  [1. 설정 저장]                                  │
│   사용자 입력 → SettingsViewModel                │
│              → AlarmRepository                   │
│              → Room DB (AlarmProfile 저장)       │
│                                                  │
│  [2. 경로 계산]                                  │
│   ScheduleAlarmUseCase                           │
│   → ODsay API (출발지+목적지 → 경로 후보 목록)    │
│   → RouteRepository → Room DB (캐시 저장)        │
│   → D2D 총 소요시간 계산                         │
│   → 기상 보정 (WeatherRepository → 기상청 API)   │
│   → AlarmManager 기상 알람 예약                  │
│                                                  │
│  [3. 실시간 모니터링]  ← WorkManager 5분 주기    │
│   TrafficMonitorWorker                           │
│   → ODsay API (현재 경로 소요시간 재계산)         │
│   → 서울 버스 API (타야 할 버스 도착 정보)         │
│   → 서울 지하철 API (지연 여부 확인)              │
│   → 변경 감지 → ScheduleAlarmUseCase 재계산      │
│   → 변경 있음 → 재알림 NotificationCompat        │
│                                                  │
│  [4. 알람 발생]                                  │
│   AlarmManager → BroadcastReceiver               │
│   → AlarmActivity (전체화면 알림)                 │
│   → 로컬 알림 (NotificationCompat)               │
│                                                  │
│  [5. 도착 감지]                                  │
│   Geofencing API → GeofenceReceiver              │
│   → GEOFENCE_TRANSITION_DWELL 이벤트             │
│   → HistoryRepository → 실제 도착 시각 기록       │
│   → 모니터링 비활성화                            │
└─────────────────────────────────────────────────┘
       │                    │
       ▼                    ▼
┌────────────┐    ┌──────────────────────────────┐
│  로컬 알림  │    │       외부 API                │
│ (기기 내)  │    │  ODsay Lab / 서울 버스 API /   │
└────────────┘    │  서울 지하철 API / 기상청 API  │
                  └──────────────────────────────┘
```

> 서버 없음. 모든 처리는 기기 내에서 완결됨. 외부로 나가는 데이터는 API 호출용 좌표/정류장 ID만.

---

## 3. 외부 API 연동 구조

### 3.1 API 역할 분담

| API | 역할 | 호출 시점 | 한도 |
|-----|------|----------|------|
| **ODsay Lab** (주) | 대중교통 경로 계산, 환승 정보, 실시간 도착 | 경로 계산, 모니터링 갱신 | 일 1,000회 무료 |
| **Tmap** (보조) | ODsay 한도 초과 시 경로 계산 폴백 | ODsay 호출 실패/한도 초과 시 | 별도 |
| **서울열린데이터광장 버스 API** | 서울 버스 실시간 도착 (직접 연동 보조) | 모니터링 중 특정 버스 확인 | 무료 |
| **서울열린데이터광장 지하철 API** | 서울 지하철 실시간 위치·지연 | 모니터링 중 지하철 노선 확인 | 무료 |
| **기상청 단기예보 API** | 3시간 단위 강수 예보 | WeatherCheckWorker (3시간 주기) | 무료 |
| **기상청 초단기실황 API** | 현재 강수량(mm) | 모니터링 시작 시, 알람 직전 | 무료 |

### 3.2 ODsay API 호출 전략

```
일일 1,000회 한도 관리:
- 호출 횟수를 DataStore에 날짜별로 기록
- 950회 도달 시 Tmap 폴백으로 자동 전환
- 자정에 카운터 리셋
- 모니터링 주기: 정상 5분 → 이상 감지 시 1분 (호출 절약)
```

### 3.3 기상 보정 로직

```kotlin
// 강수량(mm) → 보정 계수
fun WeatherCorrection.toMultiplier(userFactor: Float = 1.0f): Float {
    val base = when {
        rainfall < 1f  -> 1.00f
        rainfall < 5f  -> 1.05f
        rainfall < 10f -> 1.15f
        else           -> 1.25f
    }
    return base * userFactor  // 사용자 설정 계수 반영
}

// D2D 보정 적용
correctedD2D = baseDuration * multiplier
```

### 3.4 API 호출 시퀀스 (모니터링 중)

```
TrafficMonitorWorker (5분 주기)
  │
  ├─[1] ODsay API: 현재 경로 소요시간 재계산
  │       실패 시 → Tmap API 폴백
  │       폴백도 실패 → Room 캐시 사용 + "실시간 정보 없음" 표시
  │
  ├─[2] 서울 버스 API: 탑승 예정 버스 도착 정보 조회
  │
  ├─[3] 서울 지하철 API: 탑승 예정 노선 지연 여부 조회
  │
  ├─[4] 기상청 초단기실황 API: 현재 강수량 조회 (3시간 캐시 활용)
  │
  └─[5] 결과 비교: 이전 D2D vs 새 D2D
          변경 없음 → 다음 주기 대기
          변경 있음 → AlarmScheduler 재계산 → 재알림 발송
```

---

## 4. WorkManager 백그라운드 작업 설계

### 4.1 작업 목록

| Worker | 유형 | 주기 | 조건 |
|--------|------|------|------|
| `TrafficMonitorWorker` | PeriodicWork | 5분 (이상 감지 시 1분) | 네트워크 연결 필수 |
| `WeatherCheckWorker` | PeriodicWork | 3시간 | 네트워크 연결 필수 |
| `AlarmSchedulerWorker` | OneTimeWork | 경로 계산 완료 시 | 없음 |
| `GeofencingManager` | 시스템 API (별도) | 연속 | 위치 권한 필수 |

### 4.2 TrafficMonitorWorker 설계

```
시작 조건: 모니터링 시작 시각 도달 (AlarmManager가 WorkManager 체인 시작)
종료 조건: 도착 목표 시각 + 30분 경과 OR GeofencingManager 도착 감지

작업 흐름:
  1. DataStore에서 오늘 알람 프로필 로드
  2. ODsay API 경로 재계산 (캐시 비교)
  3. 버스/지하철 실시간 정보 조회
  4. D2D 변화량 > 2분이면 AlarmManager 알람 재스케줄링 + 재알림
  5. 다음 주기 예약 (정상: 5분, 이상: 1분)

Doze 대응:
  - setRequiredNetworkType(NetworkType.CONNECTED)
  - 알람 시각 직전에는 AlarmManager.setExactAndAllowWhileIdle 사용
```

### 4.3 알람 스케줄링 흐름

```
AlarmSchedulerWorker
  │
  ├─ 목표 도착 시각 - D2D 총 소요시간 - 준비 시간 = 기상 시각
  │
  ├─ AlarmManager.setExactAndAllowWhileIdle(기상 시각)
  │      → BroadcastReceiver: AlarmReceiver
  │             → AlarmActivity (전체화면) + NotificationCompat
  │
  └─ AlarmManager.setExactAndAllowWhileIdle(출발 시각 - 5분)
         → 출발 준비 알림 NotificationCompat
```

### 4.4 Geofencing 설계

```
목적지 등록 시:
  GeofencingClient.addGeofences(
    Geofence(
      requestId = destinationId,
      radius = 200f,       // 200m 반경
      transitionTypes = GEOFENCE_TRANSITION_DWELL,
      loiteringDelay = 60_000  // 1분 체류 후 감지
    )
  )

GeofenceReceiver.onReceive():
  → DWELL 이벤트 → HistoryRepository.recordArrival(실제 도착 시각)
  → WorkManager: TrafficMonitorWorker 취소
  → AlarmManager: 미발생 알람 취소
```

---

## 5. 핵심 데이터 모델

### AlarmProfile

```kotlin
// Domain Model
data class AlarmProfile(
    val id: Long = 0,
    val name: String,                     // "출근"
    val origin: Location,                 // 출발지
    val destination: Location,            // 목적지
    val targetArrivalTime: LocalTime,     // 09:00
    val preparationMinutes: Int = 30,     // 준비 시간
    val monitoringStartTime: LocalTime,   // 07:00
    val activeDays: Set<DayOfWeek>,       // 월~금
    val isEnabled: Boolean = true,
    val weatherCorrectionFactor: Float = 1.0f  // 사용자 설정 계수
)

data class Location(
    val latitude: Double,
    val longitude: Double,
    val address: String
)
```

### Route

```kotlin
data class Route(
    val id: Long = 0,
    val profileId: Long,
    val legs: List<RouteLeg>,             // 구간 목록
    val totalDurationMinutes: Int,        // D2D 총 소요 (보정 전)
    val correctedDurationMinutes: Int,    // 기상 보정 후
    val calculatedAt: Instant,
    val source: RouteSource               // ODSAY / TMAP / CACHE
)

data class RouteLeg(
    val type: LegType,                    // WALK / BUS / SUBWAY
    val durationMinutes: Int,
    val distanceMeters: Int,
    val transitInfo: TransitInfo?         // 버스/지하철 정보
)

enum class LegType { WALK, BUS, SUBWAY, TRANSFER_WAIT }
enum class RouteSource { ODSAY, TMAP, CACHE }
```

### TransitInfo

```kotlin
data class TransitInfo(
    val type: LegType,
    val lineId: String,                   // 버스 노선 ID / 지하철 노선 코드
    val lineName: String,                 // "271" / "2호선"
    val boardingStop: StopInfo,
    val alightingStop: StopInfo,
    val realtimeArrivalMinutes: Int?,     // 실시간 도착까지 남은 분 (null = 정보 없음)
    val isDelayed: Boolean = false,
    val delayMinutes: Int = 0
)

data class StopInfo(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double
)
```

### WeatherInfo

```kotlin
data class WeatherInfo(
    val rainfall: Float,                  // 강수량 mm
    val precipitationProbability: Int,    // 강수 확률 %
    val forecastTime: Instant,
    val correctionMultiplier: Float       // 계산된 보정 계수
)
```

### AlarmHistory

```kotlin
data class AlarmHistory(
    val id: Long = 0,
    val profileId: Long,
    val date: LocalDate,
    val scheduledWakeTime: LocalTime,     // 예정 기상 시각
    val scheduledDepartureTime: LocalTime,
    val predictedArrivalTime: LocalTime,
    val actualArrivalTime: LocalTime?,    // Geofencing 감지값 (null = 미기록)
    val d2dPredictedMinutes: Int,
    val d2dActualMinutes: Int?            // 실제 소요 (도착 감지 시 계산)
)
```

---

## 6. 보안 설계 결정

### 6.1 API 키 관리

```
저장 위치: local.properties (git 제외) → BuildConfig 필드로 주입
빌드 시:  ODSAY_API_KEY=xxxx → BuildConfig.ODSAY_API_KEY
런타임:   Android Keystore에 암호화 저장 (앱 설치 후 첫 실행 시 이동)
배포 시:  R8 전체 난독화 활성화 (minifyEnabled = true)
```

### 6.2 위치 정보 보호

```
저장:  Room DB + SQLCipher 암호화 (또는 EncryptedSharedPreferences)
전송:  API 호출 시 좌표 쌍만 전송 (출발지 lat/lon, 목적지 lat/lon)
보관:  AlarmHistory 내 위치는 정류장 ID(비개인정보)로 대체 저장
삭제:  30일 경과 데이터 자동 삭제 스케줄러
```

### 6.3 컴포넌트 보안

```xml
<!-- AndroidManifest.xml -->
<receiver android:name=".AlarmReceiver"
          android:exported="false" />  <!-- 외부 앱 호출 차단 -->

<service android:name=".GeofenceService"
         android:exported="false" />

<!-- 권한 최소화 -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<!-- FCM 관련 권한 없음 (로컬 알림만) -->
```

---

## 7. 모듈 구조 (패키지)

```
com.example.smartalarm/
├── presentation/
│   ├── onboarding/        # OnboardingFragment + ViewModel
│   ├── home/              # HomeScreen (다음 알람 요약)
│   ├── route/             # RouteScreen (경로 상세)
│   ├── settings/          # SettingsScreen (프로필 편집, 우천 계수)
│   └── alarm/             # AlarmActivity (전체화면 알람)
├── domain/
│   ├── model/             # AlarmProfile, Route, TransitInfo, WeatherInfo, AlarmHistory
│   ├── repository/        # Repository 인터페이스
│   └── usecase/           # CalculateRouteUseCase 등
├── data/
│   ├── remote/
│   │   ├── odsay/         # OdsayApiService + DTO + Mapper
│   │   ├── tmap/          # TmapApiService + DTO + Mapper
│   │   ├── seoulbus/      # SeoulBusApiService + DTO + Mapper
│   │   ├── subway/        # SubwayApiService + DTO + Mapper
│   │   └── weather/       # WeatherApiService + DTO + Mapper
│   ├── local/
│   │   ├── db/            # AppDatabase, Dao 인터페이스들
│   │   └── datastore/     # SettingsDataStore
│   ├── repository/        # Repository 구현체
│   └── background/
│       ├── worker/        # TrafficMonitorWorker, WeatherCheckWorker, AlarmSchedulerWorker
│       └── geofence/      # GeofencingManager, GeofenceReceiver
└── di/                    # Hilt Module
```

---

*다음 단계: test-engineer 투입 → TDD 기반 UseCase 단위 테스트 작성 후 implementation 시작*
