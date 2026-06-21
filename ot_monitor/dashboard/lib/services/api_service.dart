import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/telemetry.dart';
import 'app_config.dart';

/// REST client for the backend. The backend uses cookie-based sessions, so we
/// capture the Set-Cookie header on login and replay it on later requests
/// (the `http` package does not persist cookies on its own).
class ApiService {
  String? _cookie;
  String? username;
  String? role;

  bool get isLoggedIn => _cookie != null;
  bool get isAdmin => role == 'admin';

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_cookie != null) 'Cookie': _cookie!,
      };

  Future<bool> login(String user, String password) async {
    try {
      final r = await http.post(
        Uri.parse('${AppConfig.httpBase}/auth/login'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({'username': user, 'password': password}),
      );
      if (r.statusCode == 200) {
        final raw = r.headers['set-cookie'];
        if (raw != null && raw.isNotEmpty) _cookie = raw.split(';').first;
        final j = jsonDecode(r.body) as Map<String, dynamic>;
        username = j['username']?.toString();
        role = j['role']?.toString();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> logout() async {
    try {
      await http.post(Uri.parse('${AppConfig.httpBase}/auth/logout'),
          headers: _headers);
    } catch (_) {}
    _cookie = null;
    username = null;
    role = null;
  }

  /// Historical telemetry rows for the last [hours] hours.
  /// Columns: timestamp_iso, temperature_c, relative_humidity_pct,
  /// pm1_ugm3, pm25_ugm3, pm10_ugm3, diff_pressure_pa, co2_ppm, voc_ppb,
  /// door_state, system_status.
  Future<List<Map<String, dynamic>>> getHistory({double hours = 1}) async {
    final r = await http.get(
      Uri.parse('${AppConfig.httpBase}/history?hours=$hours'),
      headers: _headers,
    );
    if (r.statusCode != 200) {
      throw Exception('History request failed (${r.statusCode})');
    }
    final j = jsonDecode(r.body) as Map<String, dynamic>;
    return ((j['data'] as List?) ?? [])
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .toList();
  }

  Future<List<AlarmEventModel>> getAlarms({int limit = 100}) async {
    final r = await http.get(
      Uri.parse('${AppConfig.httpBase}/alarms?limit=$limit'),
      headers: _headers,
    );
    if (r.statusCode != 200) {
      throw Exception('Alarms request failed (${r.statusCode})');
    }
    final j = jsonDecode(r.body) as Map<String, dynamic>;
    return ((j['alarms'] as List?) ?? [])
        .whereType<Map>()
        .map((e) => AlarmEventModel.fromJson(e.cast<String, dynamic>()))
        .toList();
  }

  /// Acknowledge an alarm (admin only). Returns true on success.
  Future<bool> acknowledgeAlarm(int id) async {
    try {
      final by = Uri.encodeComponent(username ?? 'admin');
      final r = await http.post(
        Uri.parse('${AppConfig.httpBase}/alarms/$id/acknowledge?ack_by=$by'),
        headers: _headers,
      );
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getThresholds() async {
    final r = await http.get(
      Uri.parse('${AppConfig.httpBase}/settings/thresholds'),
      headers: _headers,
    );
    if (r.statusCode != 200) {
      throw Exception('Thresholds request failed (${r.statusCode})');
    }
    return jsonDecode(r.body) as Map<String, dynamic>;
  }
}
