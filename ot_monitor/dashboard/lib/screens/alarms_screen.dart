import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/telemetry.dart';
import '../providers/dashboard_provider.dart';
import '../theme/app_theme.dart';

class AlarmsScreen extends StatefulWidget {
  const AlarmsScreen({super.key});

  @override
  State<AlarmsScreen> createState() => _AlarmsScreenState();
}

class _AlarmsScreenState extends State<AlarmsScreen> {
  List<AlarmEventModel> _alarms = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = context.read<DashboardProvider>().api;
      final list = await api.getAlarms(limit: 200);
      if (mounted) setState(() => _alarms = list);
    } catch (e) {
      if (mounted) setState(() => _error = 'Could not load alarms: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _acknowledge(AlarmEventModel a) async {
    final api = context.read<DashboardProvider>().api;
    if (!api.isAdmin) {
      _snack('Sign in as an admin to acknowledge alarms.');
      return;
    }
    if (a.id == null) return;
    final ok = await api.acknowledgeAlarm(a.id!);
    _snack(ok ? 'Alarm acknowledged.' : 'Acknowledge failed.');
    if (ok) _load();
  }

  void _snack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(msg)));
  }

  String _fmtTime(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      return DateFormat('dd MMM, HH:mm:ss').format(dt);
    } catch (_) {
      return iso;
    }
  }

  String _prettyParam(String p) =>
      p.replaceAll('combination.', '').replaceAll('_', ' ').toUpperCase();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Text('Alarm Log',
                  style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary)),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Refresh'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(child: _body()),
        ],
      ),
    );
  }

  Widget _body() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.accent));
    }
    if (_error != null) {
      return Center(
          child: Text(_error!, style: const TextStyle(color: AppColors.alarm)));
    }
    if (_alarms.isEmpty) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle_outline_rounded,
                size: 48, color: AppColors.normal),
            SizedBox(height: 12),
            Text('No alarms recorded.',
                style: TextStyle(color: AppColors.textSecondary)),
          ],
        ),
      );
    }
    return ListView.separated(
      itemCount: _alarms.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, i) => _alarmTile(_alarms[i]),
    );
  }

  Widget _alarmTile(AlarmEventModel a) {
    final level = alarmLevelFromString(a.level);
    final color = alarmColor(level);
    final isActive = level != AlarmLevel.normal;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      _prettyParam(a.parameter),
                      style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          color: AppColors.textPrimary),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(alarmLabel(level),
                          style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: color)),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  a.message.isNotEmpty ? a.message : 'No detail',
                  style: const TextStyle(
                      fontSize: 12, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 3),
                Text(_fmtTime(a.timestampIso),
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted)),
              ],
            ),
          ),
          if (a.acknowledged)
            Row(
              children: [
                const Icon(Icons.check_rounded,
                    size: 16, color: AppColors.normal),
                const SizedBox(width: 4),
                Text('Ack${a.ackBy != null ? ' · ${a.ackBy}' : ''}',
                    style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.normal,
                        fontWeight: FontWeight.w600)),
              ],
            )
          else if (isActive)
            TextButton(
              onPressed: () => _acknowledge(a),
              child: const Text('Acknowledge'),
            ),
        ],
      ),
    );
  }
}
