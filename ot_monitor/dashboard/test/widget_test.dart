// Unit tests for the telemetry model — verifies the dashboard correctly
// parses the backend DashboardPayload contract (data_model.py).

import 'package:flutter_test/flutter_test.dart';
import 'package:ot_monitor_dashboard/models/telemetry.dart';

void main() {
  test('DashboardPayload.fromJson parses the backend contract', () {
    final json = {
      'timestamp_iso': '2026-06-20T12:00:00+05:30',
      'ot_id': 'OT-01',
      'ot_name': 'Operating Theatre 1',
      'data': {
        'temperature_c': 22.4,
        'relative_humidity_pct': 52.1,
        'pm1_ugm3': 6.0,
        'pm25_ugm3': 12.0,
        'pm10_ugm3': 20.0,
        'co2_ppm': 425.0,
        'voc_ppb': 50.0,
        'diff_pressure_pa': 8.0,
        'battery_pct': 97.7,
        'power_source': 'MAINS',
        'door_state': 'CLOSED',
        'occupancy_count': null,
        'ext': {'pressure_hpa': 1013.2},
      },
      'device_health': {
        'temperature_sensor': {'ok': true},
        'pm_sensor': {'ok': false, 'error_code': 'E_CRC'},
        'storage_ok': true,
        'uptime_s': 120.5,
      },
      'system_status': 'WARNING',
      'network_status': 'LOCAL_ONLY',
      'cloud_sync': false,
      'alarm_states': {
        'pm25_ugm3': {
          'parameter': 'pm25_ugm3',
          'level': 'WARNING',
          'value': 12.0,
          'message': 'PM25: WARNING',
        },
        'temperature_c': {
          'parameter': 'temperature_c',
          'level': 'NORMAL',
          'value': 22.4,
        },
      },
      'active_alarms': [
        {
          'id': null,
          'timestamp_iso': '2026-06-20T12:00:00+05:30',
          'parameter': 'pm25_ugm3',
          'level': 'WARNING',
          'value': 12.0,
          'message': 'PM25: WARNING',
          'acknowledged': false,
        }
      ],
    };

    final p = DashboardPayload.fromJson(json);

    expect(p.otName, 'Operating Theatre 1');
    expect(p.data.temperatureC, 22.4);
    expect(p.data.batteryPct, 97.7);
    expect(p.data.powerSource, 'MAINS');
    expect(p.data.barometricHpa, 1013.2);
    expect(p.systemStatus, 'WARNING');
    expect(p.levelFor('pm25_ugm3'), AlarmLevel.warning);
    expect(p.levelFor('temperature_c'), AlarmLevel.normal);
    expect(p.levelFor('co2_ppm'), AlarmLevel.normal); // missing → defaults NORMAL
    expect(p.activeAlarms.length, 1);
    expect(p.activeAlarms.first.parameter, 'pm25_ugm3');
  });

  test('OTData tolerates missing/null fields', () {
    final d = OTData.fromJson({'temperature_c': null});
    expect(d.temperatureC, isNull);
    expect(d.doorState, 'UNKNOWN');
    expect(d.powerSource, 'UNKNOWN');
    expect(d.batteryPct, isNull);
  });
}
