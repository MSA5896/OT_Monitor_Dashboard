import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/telemetry.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

/// Central app state: holds the latest live payload, a rolling buffer for the
/// live trend chart, and the WebSocket connection status. Screens listen to it.
class DashboardProvider extends ChangeNotifier {
  final WebSocketService ws;
  final ApiService api;

  DashboardPayload? latest;
  WsState connection = WsState.connecting;

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
    ws.connect();
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
