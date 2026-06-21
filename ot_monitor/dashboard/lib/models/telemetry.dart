// Dart models mirroring the backend `DashboardPayload` contract
// (see ot_monitor/backend/data_model.py). Pushed over ws://<host>/ws at 1 Hz.

/// Per-parameter alarm level. Mirrors backend AlarmLevel enum.
/// Colours follow IEC 60601-1-8: alarm=red, warning=amber, normal=green,
/// fault=cyan (low-priority / informational).
enum AlarmLevel { normal, warning, alarm, fault }

AlarmLevel alarmLevelFromString(String? s) {
  switch ((s ?? 'NORMAL').toUpperCase()) {
    case 'ALARM':
      return AlarmLevel.alarm;
    case 'WARNING':
      return AlarmLevel.warning;
    case 'FAULT':
      return AlarmLevel.fault;
    default:
      return AlarmLevel.normal;
  }
}

double? _toD(dynamic v) => v == null ? null : (v as num).toDouble();
int? _toI(dynamic v) => v == null ? null : (v as num).toInt();

class OTData {
  final double? temperatureC;
  final double? relativeHumidityPct;
  final double? pm1;
  final double? pm25;
  final double? pm10;
  final double? co2Ppm;
  final double? vocPpb;
  final double? diffPressurePa;
  final double? batteryPct;
  final String doorState;
  final String powerSource;
  final int? occupancyCount;
  final Map<String, dynamic> ext;

  OTData({
    this.temperatureC,
    this.relativeHumidityPct,
    this.pm1,
    this.pm25,
    this.pm10,
    this.co2Ppm,
    this.vocPpb,
    this.diffPressurePa,
    this.batteryPct,
    this.doorState = 'UNKNOWN',
    this.powerSource = 'UNKNOWN',
    this.occupancyCount,
    this.ext = const {},
  });

  /// Barometric pressure (hPa) is delivered via ext on real hardware.
  double? get barometricHpa => _toD(ext['pressure_hpa']);

  factory OTData.fromJson(Map<String, dynamic> j) => OTData(
        temperatureC: _toD(j['temperature_c']),
        relativeHumidityPct: _toD(j['relative_humidity_pct']),
        pm1: _toD(j['pm1_ugm3']),
        pm25: _toD(j['pm25_ugm3']),
        pm10: _toD(j['pm10_ugm3']),
        co2Ppm: _toD(j['co2_ppm']),
        vocPpb: _toD(j['voc_ppb']),
        diffPressurePa: _toD(j['diff_pressure_pa']),
        batteryPct: _toD(j['battery_pct']),
        doorState: (j['door_state'] ?? 'UNKNOWN').toString(),
        powerSource: (j['power_source'] ?? 'UNKNOWN').toString(),
        occupancyCount: _toI(j['occupancy_count']),
        ext: (j['ext'] as Map?)?.cast<String, dynamic>() ?? const {},
      );
}

class SensorHealth {
  final bool ok;
  final String? errorCode;
  SensorHealth({required this.ok, this.errorCode});
  factory SensorHealth.fromJson(Map<String, dynamic> j) =>
      SensorHealth(ok: j['ok'] ?? true, errorCode: j['error_code']?.toString());
}

class DeviceHealth {
  final Map<String, SensorHealth> sensors;
  final bool storageOk;
  final double? uptimeS;

  DeviceHealth({
    this.sensors = const {},
    this.storageOk = true,
    this.uptimeS,
  });

  factory DeviceHealth.fromJson(Map<String, dynamic> j) {
    final sensors = <String, SensorHealth>{};
    for (final key in const [
      'temperature_sensor',
      'humidity_sensor',
      'pm_sensor',
      'pressure_sensor',
      'co2_sensor',
      'voc_sensor',
    ]) {
      if (j[key] is Map) {
        sensors[key] = SensorHealth.fromJson((j[key] as Map).cast<String, dynamic>());
      }
    }
    return DeviceHealth(
      sensors: sensors,
      storageOk: j['storage_ok'] ?? true,
      uptimeS: _toD(j['uptime_s']),
    );
  }
}

class AlarmState {
  final String parameter;
  final String level;
  final double? value;
  final String message;
  AlarmState({
    required this.parameter,
    required this.level,
    this.value,
    this.message = '',
  });
  factory AlarmState.fromJson(Map<String, dynamic> j) => AlarmState(
        parameter: (j['parameter'] ?? '').toString(),
        level: (j['level'] ?? 'NORMAL').toString(),
        value: _toD(j['value']),
        message: (j['message'] ?? '').toString(),
      );
}

class AlarmEventModel {
  final int? id;
  final String timestampIso;
  final String parameter;
  final String level;
  final double? value;
  final String message;
  final bool acknowledged;
  final String? ackBy;

  AlarmEventModel({
    this.id,
    required this.timestampIso,
    required this.parameter,
    required this.level,
    this.value,
    this.message = '',
    this.acknowledged = false,
    this.ackBy,
  });

  factory AlarmEventModel.fromJson(Map<String, dynamic> j) => AlarmEventModel(
        id: _toI(j['id']),
        timestampIso: (j['timestamp_iso'] ?? '').toString(),
        parameter: (j['parameter'] ?? '').toString(),
        level: (j['level'] ?? 'NORMAL').toString(),
        value: _toD(j['value']),
        message: (j['message'] ?? '').toString(),
        acknowledged: (j['acknowledged'] == true) || (j['acknowledged'] == 1),
        ackBy: j['ack_by']?.toString(),
      );
}

class DashboardPayload {
  final String timestampIso;
  final String otId;
  final String otName;
  final OTData data;
  final DeviceHealth health;
  final String systemStatus; // SAFE | WARNING | ALERT | FAULT
  final String networkStatus;
  final bool cloudSync;
  final Map<String, AlarmState> alarmStates;
  final List<AlarmEventModel> activeAlarms;

  DashboardPayload({
    required this.timestampIso,
    required this.otId,
    required this.otName,
    required this.data,
    required this.health,
    required this.systemStatus,
    required this.networkStatus,
    required this.cloudSync,
    required this.alarmStates,
    required this.activeAlarms,
  });

  /// Resolve the confirmed alarm level for a telemetry key
  /// (e.g. 'temperature_c', 'pm25_ugm3').
  AlarmLevel levelFor(String key) =>
      alarmLevelFromString(alarmStates[key]?.level);

  factory DashboardPayload.fromJson(Map<String, dynamic> j) {
    final states = <String, AlarmState>{};
    final raw = (j['alarm_states'] as Map?)?.cast<String, dynamic>() ?? {};
    raw.forEach((k, v) {
      if (v is Map) states[k] = AlarmState.fromJson(v.cast<String, dynamic>());
    });
    return DashboardPayload(
      timestampIso: (j['timestamp_iso'] ?? '').toString(),
      otId: (j['ot_id'] ?? '').toString(),
      otName: (j['ot_name'] ?? 'Operating Theatre').toString(),
      data: OTData.fromJson((j['data'] as Map?)?.cast<String, dynamic>() ?? {}),
      health: DeviceHealth.fromJson(
          (j['device_health'] as Map?)?.cast<String, dynamic>() ?? {}),
      systemStatus: (j['system_status'] ?? 'SAFE').toString(),
      networkStatus: (j['network_status'] ?? 'LOCAL_ONLY').toString(),
      cloudSync: j['cloud_sync'] == true,
      alarmStates: states,
      activeAlarms: ((j['active_alarms'] as List?) ?? [])
          .whereType<Map>()
          .map((e) => AlarmEventModel.fromJson(e.cast<String, dynamic>()))
          .toList(),
    );
  }
}
