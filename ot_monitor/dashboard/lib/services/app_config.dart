import 'package:shared_preferences/shared_preferences.dart';

/// Connection settings for the backend. Defaults to the local backend
/// (matches config.yaml server.port = 8001). Editable in the Settings screen
/// and persisted via shared_preferences.
class AppConfig {
  static String host = 'localhost';
  static int port = 8001;

  static String get httpBase => 'http://$host:$port';
  static String get wsUrl => 'ws://$host:$port/ws';

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    host = prefs.getString('backend_host') ?? host;
    port = prefs.getInt('backend_port') ?? port;
  }

  static Future<void> save(String newHost, int newPort) async {
    host = newHost;
    port = newPort;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('backend_host', host);
    await prefs.setInt('backend_port', port);
  }
}
