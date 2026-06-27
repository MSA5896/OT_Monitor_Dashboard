import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/telemetry.dart';
import 'app_config.dart';

enum WsState { connecting, connected, disconnected }

/// Maintains a resilient WebSocket connection to the backend `/ws` endpoint,
/// decoding each pushed DashboardPayload. Auto-reconnects with capped backoff.
class WebSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _reconnectTimer;
  int _retry = 0;
  bool _disposed = false;

  final _payloads = StreamController<DashboardPayload>.broadcast();
  final _state = StreamController<WsState>.broadcast();

  Stream<DashboardPayload> get payloads => _payloads.stream;
  Stream<WsState> get state => _state.stream;

  void connect() {
    if (_disposed) return;
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
    _sub?.cancel();
    _channel?.sink.close();
    _payloads.close();
    _state.close();
  }
}
