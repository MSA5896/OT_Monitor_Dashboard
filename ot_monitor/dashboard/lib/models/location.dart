/// A monitored critical location (OT, ICU, cleanroom, …). Admins define these;
/// nurses/stewards pick one on the Monitor screen.
///
/// Architecture: **one backend per panel/location** (the chosen approach — keeps
/// each location's data segregated and easy to diagnose). Each location therefore
/// carries the network address (host + port) of its own backend. Selecting a
/// location points the dashboard's live connection at that backend.
class CriticalLocation {
  final String id; // e.g. OT-01
  final String name; // e.g. Operating Theatre 1
  final String type; // OT | ICU | LAB | CLEANROOM | OTHER
  final String host; // backend host/IP for this location's panel
  final int port; // backend port (default 8001)

  const CriticalLocation({
    required this.id,
    required this.name,
    this.type = 'OT',
    this.host = 'localhost',
    this.port = 8001,
  });

  Map<String, dynamic> toJson() =>
      {'id': id, 'name': name, 'type': type, 'host': host, 'port': port};

  factory CriticalLocation.fromJson(Map<String, dynamic> j) => CriticalLocation(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        type: (j['type'] ?? 'OT').toString(),
        host: (j['host'] ?? 'localhost').toString(),
        port: (j['port'] is num) ? (j['port'] as num).toInt() : 8001,
      );

  static const List<String> types = ['OT', 'ICU', 'LAB', 'CLEANROOM', 'OTHER'];
}
