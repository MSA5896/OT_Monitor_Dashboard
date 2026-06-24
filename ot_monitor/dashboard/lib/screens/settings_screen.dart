import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/location.dart';
import '../models/telemetry.dart';
import '../providers/dashboard_provider.dart';
import '../services/app_config.dart';
import '../theme/app_theme.dart';

// Admin configuration panels — composed by AdminShell's permanent sidebar:
// SensorsPanel (per-sensor "slider" gauges), LocationsPanel, AccountPanel.

// ─────────────────────────────────────────────────────────────────────────────
// Sensors tab — live per-sensor gauges (the relocated "slider" data).
// ─────────────────────────────────────────────────────────────────────────────
class SensorsPanel extends StatelessWidget {
  const SensorsPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final payload = context.watch<DashboardProvider>().latest;
    if (payload == null) {
      return const Center(
        child: Text('Waiting for live data…',
            style: TextStyle(color: AppColors.textSecondary)),
      );
    }
    final d = payload.data;

    final gauges = <Widget>[
      _SensorGauge('Temperature', d.temperatureC, '°C', 15, 30,
          warnLow: 20, warnHigh: 24, alarmLow: 18, alarmHigh: 25,
          level: payload.levelFor('temperature_c')),
      _SensorGauge('Relative Humidity', d.relativeHumidityPct, '%', 20, 90,
          warnLow: 40, warnHigh: 60, alarmLow: 30, alarmHigh: 70,
          level: payload.levelFor('relative_humidity_pct')),
      _SensorGauge('PM1.0', d.pm1, 'µg/m³', 0, 50,
          warnHigh: 10, alarmHigh: 20, level: payload.levelFor('pm1_ugm3')),
      _SensorGauge('PM2.5', d.pm25, 'µg/m³', 0, 75,
          warnHigh: 12, alarmHigh: 25, level: payload.levelFor('pm25_ugm3')),
      _SensorGauge('PM10', d.pm10, 'µg/m³', 0, 100,
          warnHigh: 20, alarmHigh: 50, level: payload.levelFor('pm10_ugm3')),
      _SensorGauge('CO₂', d.co2Ppm, 'ppm', 400, 1500,
          warnHigh: 1000, alarmHigh: 1200, level: payload.levelFor('co2_ppm')),
      _SensorGauge('VOC', d.vocPpb, 'ppb', 0, 600,
          warnHigh: 200, alarmHigh: 500, level: payload.levelFor('voc_ppb')),
      _SensorGauge('Differential Pressure', d.diffPressurePa, 'Pa', -5, 25,
          level: payload.levelFor('diff_pressure_pa')),
    ];

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text(
          'Detailed per-sensor readings with safe / warning / alarm zones. '
          'This detail is hidden from the public Monitor screen.',
          style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 16),
        ...gauges,
      ],
    );
  }
}

class _SensorGauge extends StatelessWidget {
  final String label;
  final double? value;
  final String unit;
  final double min;
  final double max;
  final double? warnLow;
  final double? warnHigh;
  final double? alarmLow;
  final double? alarmHigh;
  final AlarmLevel level;

  const _SensorGauge(
    this.label,
    this.value,
    this.unit,
    this.min,
    this.max, {
    this.warnLow,
    this.warnHigh,
    this.alarmLow,
    this.alarmHigh,
    required this.level,
  });

  double _frac(double v) => ((v - min) / (max - min)).clamp(0.0, 1.0);

  @override
  Widget build(BuildContext context) {
    final color = alarmColor(level);
    final v = value;
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(label,
                  style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary)),
              const Spacer(),
              Text(v != null ? '${v.toStringAsFixed(1)} $unit' : '—',
                  style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: v != null ? color : AppColors.textMuted)),
            ],
          ),
          const SizedBox(height: 10),
          LayoutBuilder(
            builder: (context, c) {
              final w = c.maxWidth;
              return SizedBox(
                height: 16,
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    // Track
                    Positioned(
                      top: 6,
                      left: 0,
                      right: 0,
                      child: Container(
                        height: 6,
                        decoration: BoxDecoration(
                          color: AppColors.surfaceAlt,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                    // Threshold ticks
                    ..._ticks().map((t) => Positioned(
                          top: 0,
                          left: (_frac(t.$1) * w).clamp(0.0, w - 2),
                          child: Container(width: 2, height: 16, color: t.$2),
                        )),
                    // Current-value marker
                    if (v != null)
                      Positioned(
                        top: 0,
                        left: (_frac(v) * w - 7).clamp(0.0, w - 14),
                        child: Container(
                          width: 14,
                          height: 14,
                          decoration: BoxDecoration(
                            color: color,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 2),
                          ),
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('${min.toStringAsFixed(0)} $unit',
                  style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
              Text('${max.toStringAsFixed(0)} $unit',
                  style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
            ],
          ),
        ],
      ),
    );
  }

  List<(double, Color)> _ticks() {
    final out = <(double, Color)>[];
    if (warnLow != null) out.add((warnLow!, AppColors.warning));
    if (warnHigh != null) out.add((warnHigh!, AppColors.warning));
    if (alarmLow != null) out.add((alarmLow!, AppColors.alarm));
    if (alarmHigh != null) out.add((alarmHigh!, AppColors.alarm));
    return out;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Locations tab — admin manages the critical locations nurses can monitor.
// ─────────────────────────────────────────────────────────────────────────────
class LocationsPanel extends StatelessWidget {
  const LocationsPanel({super.key});

  Future<void> _addDialog(BuildContext context) async {
    final provider = context.read<DashboardProvider>();
    final idC = TextEditingController();
    final nameC = TextEditingController();
    final hostC = TextEditingController(text: 'localhost');
    final portC = TextEditingController(text: '8001');
    String type = 'OT';
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          backgroundColor: AppColors.surface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('Add critical location'),
          content: SizedBox(
            width: 360,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: idC,
                  decoration: const InputDecoration(
                      labelText: 'ID (e.g. OT-02)', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: nameC,
                  decoration: const InputDecoration(
                      labelText: 'Name (e.g. Operating Theatre 2)',
                      border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: type,
                  decoration: const InputDecoration(
                      labelText: 'Type', border: OutlineInputBorder()),
                  items: CriticalLocation.types
                      .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                      .toList(),
                  onChanged: (v) => setLocal(() => type = v ?? 'OT'),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: hostC,
                        decoration: const InputDecoration(
                            labelText: 'Backend host / IP',
                            helperText: 'Panel running this location\'s backend',
                            border: OutlineInputBorder()),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: portC,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: 'Port', border: OutlineInputBorder()),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel')),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Add'),
            ),
          ],
        ),
      ),
    );
    if (result == true) {
      final id = idC.text.trim();
      final name = nameC.text.trim();
      if (id.isEmpty || name.isEmpty) return;
      if (provider.locations.any((l) => l.id == id)) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('A location with ID "$id" already exists.')));
        }
        return;
      }
      await provider.addLocation(CriticalLocation(
        id: id,
        name: name,
        type: type,
        host: hostC.text.trim().isEmpty ? 'localhost' : hostC.text.trim(),
        port: int.tryParse(portC.text.trim()) ?? 8001,
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
          child: Row(
            children: [
              const Expanded(
                child: Text(
                  'Locations nurses/stewards can select on the Monitor screen.',
                  style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                ),
              ),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
                onPressed: () => _addDialog(context),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('Add location'),
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
            itemCount: provider.locations.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) {
              final l = provider.locations[i];
              final selected = provider.selectedLocation?.id == l.id;
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                      color: selected ? AppColors.accent : AppColors.border),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.location_on_rounded,
                        color: AppColors.accent, size: 20),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(l.name,
                              style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textPrimary)),
                          Text('${l.id}  ·  ${l.type}  ·  ${l.host}:${l.port}',
                              style: const TextStyle(
                                  fontSize: 12, color: AppColors.textMuted)),
                        ],
                      ),
                    ),
                    if (selected)
                      const Padding(
                        padding: EdgeInsets.only(right: 8),
                        child: Text('SELECTED',
                            style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: AppColors.accent)),
                      ),
                    IconButton(
                      tooltip: 'Remove',
                      onPressed: provider.locations.length <= 1
                          ? null
                          : () => provider.removeLocation(l.id),
                      icon: const Icon(Icons.delete_outline_rounded,
                          color: AppColors.textMuted),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Account tab — backend connection + admin session.
// ─────────────────────────────────────────────────────────────────────────────
class AccountPanel extends StatefulWidget {
  const AccountPanel({super.key});

  @override
  State<AccountPanel> createState() => _AccountPanelState();
}

class _AccountPanelState extends State<AccountPanel> {
  void _snack(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    final api = provider.api;
    final loc = provider.selectedLocation;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _card('SIGNED-IN ADMIN', [
          Row(
            children: [
              const Icon(Icons.account_circle_rounded,
                  color: AppColors.accent, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  api.isLoggedIn
                      ? 'Signed in as ${api.username}  ·  role: ${api.role}'
                      : 'Not signed in',
                  style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary),
                ),
              ),
              if (api.isLoggedIn)
                OutlinedButton(
                  onPressed: () {
                    api.logout();
                    setState(() {});
                  },
                  child: const Text('Sign out'),
                ),
            ],
          ),
        ]),
        _card('ACTIVE BACKEND', [
          const Text(
            'One backend per panel: the active connection follows the selected '
            'location. Add or edit a location\'s host/port in the Locations tab.',
            style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.dns_rounded, color: AppColors.accent, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(loc != null ? '${loc.name}  (${loc.id})' : '—',
                        style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary)),
                    Text(AppConfig.httpBase,
                        style: const TextStyle(
                            fontSize: 12, color: AppColors.textMuted)),
                  ],
                ),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  provider.reconnect();
                  _snack('Reconnecting to ${AppConfig.wsUrl}');
                },
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Reconnect'),
              ),
            ],
          ),
        ]),
      ],
    );
  }

  Widget _card(String title, List<Widget> children) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: AppColors.textSecondary)),
          const SizedBox(height: 14),
          ...children,
        ],
      ),
    );
  }
}
