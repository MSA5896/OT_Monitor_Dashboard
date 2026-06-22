/// A monitored critical location (OT, ICU, cleanroom, …). Admins define these;
/// nurses/stewards pick one on the Monitor screen.
///
/// NOTE: the current backend streams a single device on one WebSocket. Until the
/// backend supports multiple devices, the selected location drives the displayed
/// name/identity while live data comes from the connected backend. See
/// REVIEW_NOTES.md ("Multi-location backend").
class CriticalLocation {
  final String id; // e.g. OT-01
  final String name; // e.g. Operating Theatre 1
  final String type; // OT | ICU | LAB | CLEANROOM | OTHER

  const CriticalLocation({
    required this.id,
    required this.name,
    this.type = 'OT',
  });

  Map<String, dynamic> toJson() => {'id': id, 'name': name, 'type': type};

  factory CriticalLocation.fromJson(Map<String, dynamic> j) => CriticalLocation(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        type: (j['type'] ?? 'OT').toString(),
      );

  static const List<String> types = ['OT', 'ICU', 'LAB', 'CLEANROOM', 'OTHER'];
}
