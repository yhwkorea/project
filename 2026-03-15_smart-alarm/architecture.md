# architecture.md — 스마트 교통 알람 설계 문서

**작성일**: 2026-03-15
**최종 수정**: 2026-03-16
**작성자**: threat-modeler
**기반**: requirements.md (CONFIRMED) + Clean Architecture + DFD Level 1

---

## 목차

1. [기술 스택](#1-기술-스택)
2. [컴포넌트 구성 (Clean Architecture)](#2-컴포넌트-구성-clean-architecture)
3. [알람 생명주기](#3-알람-생명주기)
4. [주요 데이터 흐름 (DFD Level 1)](#4-주요-데이터-흐름-dfd-level-1)
5. [외부 API 연동 구조](#5-외부-api-연동-구조)
6. [경로 미리보기](#6-경로-미리보기)
7. [WorkManager 백그라운드 작업 설계](#7-workmanager-백그라운드-작업-설계)
8. [핵심 데이터 모델](#8-핵심-데이터-모델)
9. [DB 마이그레이션](#9-db-마이그레이션)
10. [보안 설계 결정](#10-보안-설계-결정)
11. [모듈 구조 (패키지)](#11-모듈-구조-패키지)

---

## 1. 기술 스택

| 분류 | 기술 |
|------|------|
| 플랫폼 | Android, Kotlin |
| UI | Jetpack Compose |
| DI | Hilt |
| DB | Room v3 |
| 백그라운드 | WorkManager, AlarmManager |

---

## 2. 컴포넌트 구성 (Clean Architecture)

```
┌─────────────────────────────────────────────────────┐
│                  Presentation Layer                  │
│  ┌──────────────────┐   ┌─────────────────────────┐ │
│  │  Compose UI       │   │  ViewModel (StateFlow)  │ │
│  │  - HomeScreen     │◄──│  - HomeViewModel        │ │
│  │  - AlarmEditScreen│   │  - AlarmEditViewModel   │ │
│  │  - RouteMapScreen │   └────────────┬────────────┘ │
│  └──────────────────┘                │               │
└─────────────────────────────────────┼───────────────┘
                                       │ UseCase 호출
┌─────────────────────────────────────┼───────────────┐
│                  Domain Layer        │               │
│  ┌──────────────────────────────────▼─────────────┐ │
│  │                   UseCases                      │ │
│  │  - CalculateWakeTimeUseCase                     │ │
│  │  - GetOptimalRouteUseCase                       │ │
│  └──────────────────────────────────┬─────────────┘ │
│  ┌──────────────────────────────────▼─────────────┐ │
│  │              Domain Models (순수 Kotlin)         │ │
│  │  AlarmProfile / Route / RouteType /             │ │
│  │  RouteSegment                                   │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────┼───────────────┘
                                       │ Repository 인터페이스
┌─────────────────────────────────────┼───────────────┐
│                   Data Layer         │               │
│  ┌──────────────────────────────────▼─────────────┐ │
│  │                 Repositories                    │ │
│  │  - RouteRepositoryImpl  - AlarmRepositoryImpl  │ │
│  └────────────┬──────────────────────┬────────────┘ │
│               │                      │               │
│  ┌────────────▼──────────┐ ┌─────────▼────────────┐ │
│  │    Remote DataSources  │ │  Local DataSources    │ │
│  │  - OdsayApi            │ │  - AppDatabase (Room) │ │
│  │  - SeoulBusApi         │ │    (AlarmDao 등)       │ │
│  │  - SeoulSubwayApi      │ │                       │ │
│  │  - WeatherApi          │ │                       │ │
│  │    (OpenWeatherMap)    │ │                       │ │
│  └───────────────────────┘ └───────────────────────┘ │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │        Background / Alarm Layer               │   │
│  │  - TrafficMonitorWorker                       │   │
│  │  - RescheduleAlarmsWorker                     │   │
│  │  - AlarmScheduler                             │   │
│  │  - AlarmReceiver                              │   │
│  │  - BootReceiver                               │   │
│  └───────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

### 레이어별 의존 방향

```
Presentation → Domain ← Data
(Domain은 외부에 의존하지 않는 순수 비즈니스 로직)
```

---

## 3. 알람 생명주기

```
저장
  → CalculateWakeTimeUseCase (다음 활성요일 탐색)
  → AlarmScheduler.schedule(wakeTime)
  → TrafficMonitorWorker.scheduleNextMonitoring(profile)
      → OneTimeWork at (arrivalTime - monitoringStartMinutes)

모니터링 시작
  → RouteRepository.getOptimalRoute() [ODsay + 새벽필터]
  → WeatherApi.getCurrentWeather() → travelMultiplier 적용
  → AlarmScheduler.schedule(adjustedWakeTime)
  → 도착 전이면 3분 후 재실행
  → 기상시각 경과 시 즉시 발화(+3초)

알람 발화
  → AlarmReceiver → 알림 표시
  → RescheduleAlarmsWorker → 다음 날 모니터링 재예약

재부팅
  → BootReceiver → RescheduleAlarmsWorker
```

---

## 4. 주요 데이터 흐름 (DFD Level 1)

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
│   사용자 입력 → AlarmEditViewModel               │
│              → AlarmRepositoryImpl               │
│              → AppDatabase (AlarmProfile 저장)   │
│                                                  │
│  [2. 경로 계산]                                  │
│   CalculateWakeTimeUseCase                       │
│   → GetOptimalRouteUseCase                       │
│   → OdsayApi (출발지+목적지 → 경로 후보 목록)     │
│   → 새벽 운행 중단 필터 (departureMin 30..329)    │
│   → RouteRepositoryImpl → AppDatabase (캐시)     │
│   → WeatherApi.getCurrentWeather()               │
│   → travelMultiplier 적용 → wakeTime 계산        │
│   → AlarmScheduler.schedule(wakeTime)            │
│                                                  │
│  [3. 실시간 모니터링]  ← OneTimeWork 트리거       │
│   TrafficMonitorWorker                           │
│   → OdsayApi (현재 경로 소요시간 재계산)           │
│   → SeoulBusApi (타야 할 버스 도착 정보)           │
│   → SeoulSubwayApi (지연 여부 확인)              │
│   → WeatherApi → travelMultiplier 재적용         │
│   → AlarmScheduler.schedule(adjustedWakeTime)    │
│   → 도착 전이면 3분 후 재실행                    │
│   → 기상시각 경과 시 즉시 발화(+3초)              │
│                                                  │
│  [4. 알람 발화]                                  │
│   AlarmManager → AlarmReceiver                   │
│   → 알림 표시                                    │
│   → RescheduleAlarmsWorker → 다음 날 재예약       │
│                                                  │
│  [5. 재부팅 복구]                                 │
│   BootReceiver → RescheduleAlarmsWorker          │
└─────────────────────────────────────────────────┘
       │                    │
       ▼                    ▼
┌────────────┐    ┌──────────────────────────────┐
│  로컬 알림  │    │       외부 API                │
│ (기기 내)  │    │  ODsay Lab / 서울 버스 API /   │
└────────────┘    │  서울 지하철 API /             │
                  │  OpenWeatherMap               │
                  └──────────────────────────────┘
```

> 서버 없음. 모든 처리는 기기 내에서 완결됨. 외부로 나가는 데이터는 API 호출용 좌표/정류장 ID만.

---

## 5. 외부 API 연동 구조

### 5.1 API 역할 분담

| API | 용도 | 비고 |
|-----|------|------|
| **ODsay Lab** | 대중교통 경로 탐색 | 새벽 운행중단 미반영 → 앱에서 필터 |
| **Seoul Bus API** | 실시간 버스 도착 | arsId 필요 (미구현) |
| **Seoul Subway API** | 실시간 지하철 도착 | stationName 기반 |
| **OpenWeatherMap** | 현재 날씨 | 이동시간 배수(travelMultiplier) 적용 |

### 5.2 ODsay API 호출 전략

```
새벽 운행 중단 필터:
  - departureMin in 30..329 → 해당 경로 제외
  - pathType: 1=지하철, 2=버스, 3=버스+지하철

경로 선택:
  - 항상 도보(Haversine) 포함
  - 경로 선택 필수 후 저장 가능 (RouteMapScreen)
```

### 5.3 기상 보정 로직

```kotlin
// OpenWeatherMap 현재 날씨 → travelMultiplier 적용
WeatherApi.getCurrentWeather() → travelMultiplier
adjustedWakeTime = baseDuration * travelMultiplier
```

### 5.4 API 호출 시퀀스 (모니터링 중)

```
TrafficMonitorWorker
  │
  ├─[1] OdsayApi: 현재 경로 소요시간 재계산 + 새벽 필터
  │       실패 시 → AppDatabase 캐시 사용
  │
  ├─[2] SeoulBusApi: 탑승 예정 버스 도착 정보 (arsId 미구현)
  │
  ├─[3] SeoulSubwayApi: 탑승 예정 노선 지연 여부 (stationName 기반)
  │
  ├─[4] WeatherApi(OpenWeatherMap): 현재 날씨 조회
  │
  └─[5] AlarmScheduler.schedule(adjustedWakeTime)
          도착 전이면 → 3분 후 재실행
          기상시각 경과 시 → 즉시 발화(+3초)
```

---

## 6. 경로 미리보기

- ODsay pathType: 1=지하철, 2=버스, 3=버스+지하철
- 항상 도보(Haversine) 포함
- 새벽 운행 중단 필터: departureMin in 30..329 제외
- 경로 선택 필수 후 저장 가능 (RouteMapScreen에서 선택)

---

## 7. WorkManager 백그라운드 작업 설계

### 7.1 작업 목록

| Worker | 유형 | 트리거 | 조건 |
|--------|------|--------|------|
| `TrafficMonitorWorker` | OneTimeWork (자기 재스케줄) | arrivalTime - monitoringStartMinutes | 네트워크 연결 필수 |
| `RescheduleAlarmsWorker` | OneTimeWork | 알람 발화 후 / BootReceiver | 없음 |

### 7.2 TrafficMonitorWorker 설계

```
시작 조건: OneTimeWork at (arrivalTime - monitoringStartMinutes)
종료 조건: 기상시각 경과

작업 흐름:
  1. AppDatabase에서 AlarmProfile 로드
  2. OdsayApi 경로 재계산 + 새벽 필터
  3. SeoulBusApi / SeoulSubwayApi 실시간 정보 조회
  4. WeatherApi.getCurrentWeather() → travelMultiplier
  5. AlarmScheduler.schedule(adjustedWakeTime)
  6. 도착 전이면 → scheduleNextMonitoring(3분 후)
     기상시각 경과 시 → 즉시 발화(+3초)
```

### 7.3 RescheduleAlarmsWorker 설계

```
투입 시점:
  - AlarmReceiver 발화 후 (다음 날 재예약)
  - BootReceiver (재부팅 복구)

작업 흐름:
  1. AppDatabase에서 활성 AlarmProfile 전체 로드
  2. CalculateWakeTimeUseCase → 다음 활성요일 탐색
  3. AlarmScheduler.schedule(wakeTime) 재등록
  4. TrafficMonitorWorker.scheduleNextMonitoring(profile) 재등록
```

### 7.4 알람 스케줄링 흐름

```
CalculateWakeTimeUseCase
  → 다음 활성요일의 wakeTime 계산
  → AlarmScheduler.schedule(wakeTime)
      → AlarmManager.setExactAndAllowWhileIdle
          → AlarmReceiver → 알림 표시
          → RescheduleAlarmsWorker 투입
```

---

## 8. 핵심 데이터 모델

### Domain Models

```kotlin
// AlarmProfile
data class AlarmProfile(
    val id: Long = 0,
    val name: String,
    val origin: Location,
    val destination: Location,
    val targetArrivalTime: LocalTime,
    val preparationMinutes: Int = 30,
    val monitoringStartMinutes: Int,      // arrivalTime 기준 N분 전부터 모니터링
    val activeDays: Set<DayOfWeek>,
    val isEnabled: Boolean = true,
    val preferredRouteType: RouteType,    // v1→v2 추가
    val bufferMinutes: Int = 5            // v2→v3 추가
)

// Route
data class Route(
    val id: Long = 0,
    val profileId: Long,
    val segments: List<RouteSegment>,
    val totalDurationMinutes: Int,
    val source: String                    // "ODSAY" | "CACHE"
)

// RouteSegment
data class RouteSegment(
    val type: RouteType,
    val durationMinutes: Int,
    val distanceMeters: Int,
    val transitInfo: TransitInfo?
)

enum class RouteType { WALK, BUS, SUBWAY }
```

---

## 9. DB 마이그레이션

| 버전 | 변경 내용 |
|------|----------|
| v1 | 초기 스키마 (AlarmProfile 기본 필드) |
| v2 | `preferredRouteType` 컬럼 추가 |
| v3 | `bufferMinutes` 컬럼 추가 (default 5) |

```kotlin
// Room DB 버전
@Database(entities = [...], version = 3)
abstract class AppDatabase : RoomDatabase()

// Migration 1→2
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE alarm_profile ADD COLUMN preferredRouteType TEXT NOT NULL DEFAULT 'BUS'")
    }
}

// Migration 2→3
val MIGRATION_2_3 = object : Migration(2, 3) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE alarm_profile ADD COLUMN bufferMinutes INTEGER NOT NULL DEFAULT 5")
    }
}
```

---

## 10. 보안 설계 결정

### 10.1 API 키 관리

```
저장 위치: local.properties (git 제외) → BuildConfig 필드로 주입
빌드 시:  ODSAY_API_KEY=xxxx → BuildConfig.ODSAY_API_KEY
런타임:   Android Keystore에 암호화 저장 (앱 설치 후 첫 실행 시 이동)
배포 시:  R8 전체 난독화 활성화 (minifyEnabled = true)
```

### 10.2 위치 정보 보호

```
저장:  Room DB + SQLCipher 암호화
전송:  API 호출 시 좌표 쌍만 전송 (출발지 lat/lon, 목적지 lat/lon)
삭제:  30일 경과 데이터 자동 삭제 스케줄러
```

### 10.3 컴포넌트 보안

```xml
<!-- AndroidManifest.xml -->
<receiver android:name=".AlarmReceiver"
          android:exported="false" />

<receiver android:name=".BootReceiver"
          android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.BOOT_COMPLETED" />
    </intent-filter>
</receiver>

<!-- 권한 최소화 -->
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
<!-- FCM 관련 권한 없음 (로컬 알림만) -->
```

---

## 11. 모듈 구조 (패키지)

```
com.example.smartalarm/
├── presentation/
│   ├── home/              # HomeScreen, HomeViewModel
│   ├── alarmedit/         # AlarmEditScreen, AlarmEditViewModel
│   └── routemap/          # RouteMapScreen
├── domain/
│   ├── model/             # AlarmProfile, Route, RouteType, RouteSegment
│   ├── repository/        # Repository 인터페이스
│   └── usecase/           # CalculateWakeTimeUseCase, GetOptimalRouteUseCase
├── data/
│   ├── remote/
│   │   ├── odsay/         # OdsayApi + DTO + Mapper
│   │   ├── seoulbus/      # SeoulBusApi + DTO + Mapper
│   │   ├── seoulsubway/   # SeoulSubwayApi + DTO + Mapper
│   │   └── weather/       # WeatherApi (OpenWeatherMap) + DTO + Mapper
│   ├── local/
│   │   └── db/            # AppDatabase, Dao, Migration
│   └── repository/        # RouteRepositoryImpl, AlarmRepositoryImpl
├── alarm/
│   ├── AlarmScheduler.kt
│   ├── AlarmReceiver.kt
│   └── BootReceiver.kt
├── worker/
│   ├── TrafficMonitorWorker.kt
│   └── RescheduleAlarmsWorker.kt
└── di/                    # Hilt Module
```

---

*최종 수정: 2026-03-16 — Room v3, OpenWeatherMap, 알람 생명주기 플로우, DB 마이그레이션 이력 반영*
