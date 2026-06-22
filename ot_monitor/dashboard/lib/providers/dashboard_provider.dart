import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/location.dart';
import '../models/telemetry.dart';
import '../services/api_service.dart';
import '../services/locations_service.dart';
import '../services/websocket_service.dart';

/// Central app state: latest live payload, rolling buffer for the live trend,
/// WebSocket status, the admin-defined critical locations + current selection,
/// and admin auth (delegated to ApiService).
class DashboardProvider extends ChangeNotifier {
  final WebSocketService ws;
  final ApiService api;
  final LocationsService _locations = LocationsService();

  DashboardPayload? latest;
  WsState connection = WsState.connecting;

  List<CriticalLocation> locations = const [];
  CriticalLocation? selectedLocation;

  /// Rolling buffer of recent payloads for the live trend (≈ last 2 minutes).
  final List<DashboardPayload> liveBuffer = [];
  static const int _maxBuffer = 120;

  late final StreamSubscription _paySub;
  late final StreamSubscription _stateSub;

  DashboardProvider(this.ws, this.api) {
    _paySub = ws.payloads.listen(_onPayload);
    _stateSub = ws.state.listen((s) {
      connection = s;
      notifyListeners();
    });
    _initLocations();
    ws.connect();
  }

  bool get isAdmin => api.isAdmin;

  Future<void> _initLocations() async {
    locations = await _locations.load();
    final savedId = await _locations.loadSelectedId();
    selectedLocation = locations.firstWhere(
      (l) => l.id == savedId,
      orElse: () => locations.first,
    );
    notifyListeners();
  }

  void selectLocation(CriticalLocation loc) {
    selectedLocation = loc;
    _locations.saveSelectedId(loc.id);
    notifyListeners();
  }

  Future<void> addLocation(CriticalLocation loc) async {
    locations = [...locations, loc];
    await _locations.save(locations);
    selectedLocation ??= loc;
    notifyListeners();
  }

  Future<void> removeLocation(String id) async {
    if (locations.length <= 1) return; // keep at least one
    locations = locations.where((l) => l.id != id).toList();
    if (selectedLocation?.id == id) {
      selectedLocation = locations.first;
      _locations.saveSelectedId(selectedLocation!.id);
    }
    await _locations.save(locations);
    notifyListeners();
  }

  void _onPayload(DashboardPayload p) {
    latest = p;
    liveBuffer.add(p);
    if (liveBuffer.length > _maxBuffer) {
      liveBuffer.removeRange(0, liveBuffer.length - _maxBuffer);
    }
    notifyListeners();
  }

  void reconnect() => ws.reconnectNow();

  @override
  void dispose() {
    _paySub.cancel();
    _stateSub.cancel();
    super.dispose();
  }
}
