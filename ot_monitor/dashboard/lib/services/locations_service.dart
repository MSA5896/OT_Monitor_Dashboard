import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/location.dart';

/// Persists the admin-defined list of critical locations (and the current
/// selection) in shared_preferences.
class LocationsService {
  static const _kList = 'critical_locations';
  static const _kSelected = 'selected_location_id';

  /// Seeded with the backend's default OT so the app is usable out of the box.
  static const List<CriticalLocation> _defaults = [
    CriticalLocation(
      id:   'OT-01',
      name: 'Operating Theatre 1',
      type: 'OT',
      host: 'ot-monitor.local',   // RPi mDNS hostname — change to IP in Settings if needed
      port: 8001,
    ),
  ];

  Future<List<CriticalLocation>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kList);
    if (raw == null || raw.isEmpty) return List.of(_defaults);
    try {
      final list = (jsonDecode(raw) as List)
          .whereType<Map>()
          .map((e) => CriticalLocation.fromJson(e.cast<String, dynamic>()))
          .toList();
      return list.isEmpty ? List.of(_defaults) : list;
    } catch (_) {
      return List.of(_defaults);
    }
  }

  Future<void> save(List<CriticalLocation> locations) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        _kList, jsonEncode(locations.map((l) => l.toJson()).toList()));
  }

  Future<String?> loadSelectedId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kSelected);
  }

  Future<void> saveSelectedId(String id) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kSelected, id);
  }
}
