import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/telemetry.dart';
import 'app_config.dart';

enum WsState { connecting, connected, disconnected }

/// Maintains a resilient WebSocket connection to the backend `/ws` endpoint,
/// decoding each pushed DashboardPayload. Auto-reconnects with capped backoff.
///
/// Set [demoMode] = true before calling [connect] to stream generated data
/// locally without a real backend.
class WebSocketService {
  static bool demoMode = false;

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _reconnectTimer;
  Timer? _demoTimer;
  int _retry = 0;
  bool _disposed = false;
  final _rng = Random();
  int _demoTick = 0;

  final _payloads = StreamController<DashboardPayload>.broadcast();
  final _state = StreamController<WsState>.broadcast();

  Stream<DashboardPayload> get payloads => _payloads.stream;
  Stream<WsState> get state => _state.stream;

  void connect() {
    if (_disposed) return;
    if (demoMode) {
      _state.add(WsState.connected);
      _demoTimer?.cancel();
      _demoTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!_disposed) _payloads.add(_demoPayload());
      });
      return;
    }
    _state.add(WsState.connecting);
    try {
      _channel = WebSocketChannel.connect(Uri.parse(AppConfig.wsUrl));
      _sub = _channel!.stream.listen(
        (msg) {
          _retry = 0;
          _state.add(WsState.connected);
          try {
            final decoded = jsonDecode(msg as String) as Map<String, dynamic>;
            _payloads.add(DashboardPayload.fromJson(decoded));
          } catch (_) {
            // Ignore malformed frames; keep the connection alive.
          }
        },
        onDone: _scheduleReconnect,
        onError: (_) => _scheduleReconnect(),
        cancelOnError: true,
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  /// Force an immediate reconnect (e.g. after the user changes the backend host).
  void reconnectNow() {
    _reconnectTimer?.cancel();
    _retry = 0;
    _sub?.cancel();
    _channel?.sink.close();
    connect();
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    _state.add(WsState.disconnected);
    _sub?.cancel();
    _retry = (_retry + 1).clamp(1, 6);
    final delaySeconds = _retry * 2; // 2,4,6 … capped at 12s
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delaySeconds), connect);
  }

  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _demoTimer?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
    _payloads.close();
    _state.close();
  }

  double _jitter(double base, double range) =>
      base + (_rng.nextDouble() * 2 - 1) * range;

  DashboardPayload _demoPayload() {
    _demoTick++;
    // Slow sine wave on temperature to simulate drift
    final tempBase = 21.0 + sin(_demoTick / 30) * 0.8;
    final pm25 = _jitter(3.2, 0.6).clamp(0.5, 12.0);
    final pm10 = _jitter(7.1, 1.0).clamp(1.0, 20.0);

    final data = OTData(
      temperatureC: _jitter(tempBase, 0.1),
      relativeHumidityPct: _jitter(55.0, 0.8),
      pm1: _jitter(1.8, 0.4).clamp(0.1, 8.0),
      pm25: pm25,
      pm10: pm10,
      co2Ppm: _jitter(480.0, 8.0),
      vocPpb: _jitter(72.0, 5.0),
      diffPressurePa: _jitter(18.5, 0.5),
      batteryPct: 96.0,
      doorState: 'CLOSED',
      powerSource: 'MAINS',
      occupancyCount: 4,
    );

    return DashboardPayload(
      timestampIso: DateTime.now().toIso8601String(),
      otId: 'OT-01',
      otName: 'Theatre 1 — Demo',
      data: data,
      health: DeviceHealth(
        sensors: {
          'temperature_sensor': SensorHealth(ok: true),
          'humidity_sensor': SensorHealth(ok: true),
          'pm_sensor': SensorHealth(ok: true),
          'pressure_sensor': SensorHealth(ok: true),
          'co2_sensor': SensorHealth(ok: true),
          'voc_sensor': SensorHealth(ok: true),
        },
        storageOk: true,
        uptimeS: _demoTick.toDouble(),
      ),
      systemStatus: 'SAFE',
      networkStatus: 'DEMO',
      cloudSync: false,
      alarmStates: {},
      activeAlarms: [],
    );
  }
}
