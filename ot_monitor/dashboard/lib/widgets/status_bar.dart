/// status_bar.dart – Bottom status bar: OT status pill, connectivity, clock.

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/telemetry.dart';
import '../providers/dashboard_provider.dart';
import '../services/websocket_service.dart' as ws;
import '../theme/app_theme.dart';

class StatusBar extends StatefulWidget {
  const StatusBar({super.key});

  @override
  State<StatusBar> createState() => _StatusBarState();
}

class _StatusBarState extends State<StatusBar> {
  late Timer _clockTimer;
  DateTime _now = DateTime.now();

  @override
  void initState() {
    super.initState();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _clockTimer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    final status   = provider.systemStatus;
    final connState = provider.connectionState;

    return Container(
      height: 52,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(
          top: BorderSide(color: AppColors.border, width: 1),
        ),
      ),
      child: Row(
        children: [
          // ── OT Status pill ───────────────────────────────────────────────
          _OtStatusPill(status: status),

          const SizedBox(width: 20),
          Container(width: 1, height: 28, color: AppColors.border),
          const SizedBox(width: 20),

          // ── Connectivity ─────────────────────────────────────────────────
          _ConnectivityIndicator(state: connState),

          const SizedBox(width: 20),
          Container(width: 1, height: 28, color: AppColors.border),
          const SizedBox(width: 20),

          // ── Cloud Sync ───────────────────────────────────────────────────
          _CloudSyncIndicator(
              synced: provider.payload?.cloudSync ?? false),

          const Spacer(),

          // ── Clock ────────────────────────────────────────────────────────
          _ClockDisplay(now: _now),
        ],
      ),
    );
  }
}

// ── OT Status pill ──────────────────────────────────────────────────────────

class _OtStatusPill extends StatelessWidget {
  final SystemStatus status;
  const _OtStatusPill({required this.status});

  Color get _color {
    switch (status) {
      case SystemStatus.SAFE:    return AppColors.safe;
      case SystemStatus.WARNING: return AppColors.warning;
      case SystemStatus.ALERT:   return AppColors.alarm;
      case SystemStatus.FAULT:   return AppColors.fault;
    }
  }

  IconData get _icon {
    switch (status) {
      case SystemStatus.SAFE:    return Icons.check_circle_rounded;
      case SystemStatus.WARNING: return Icons.warning_rounded;
      case SystemStatus.ALERT:   return Icons.error_rounded;
      case SystemStatus.FAULT:   return Icons.report_problem_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _color.withOpacity(0.6), width: 1.5),
        boxShadow: [BoxShadow(color: _color.withOpacity(0.2), blurRadius: 8)],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('OT STATUS',
              style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textMuted,
                  letterSpacing: 1.2)),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
            decoration: BoxDecoration(
              color: _color,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(_icon, color: Colors.black, size: 13),
                const SizedBox(width: 5),
                Text(status.name,
                    style: const TextStyle(
                        color: Colors.black,
                        fontSize: 11,
                        fontWeight: FontWeight.w800)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Connectivity indicator ────────────────────────────────────────────────────

class _ConnectivityIndicator extends StatelessWidget {
  final ws.ConnectionState state;
  const _ConnectivityIndicator({required this.state});

  @override
  Widget build(BuildContext context) {
    final bool ok = state == ws.ConnectionState.connected;
    final Color c = ok ? AppColors.safe : AppColors.warning;
    final IconData ic = ok ? Icons.wifi_rounded : Icons.wifi_off_rounded;
    final String label = ok ? 'Connected'
        : state == ws.ConnectionState.reconnecting ? 'Reconnecting…'
        : state == ws.ConnectionState.connecting   ? 'Connecting…'
        : 'Offline';

    return Row(children: [
      Icon(ic, color: c, size: 17),
      const SizedBox(width: 6),
      Text(label,
          style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w500, color: c)),
    ]);
  }
}

// ── Cloud sync indicator ──────────────────────────────────────────────────────

class _CloudSyncIndicator extends StatelessWidget {
  final bool synced;
  const _CloudSyncIndicator({required this.synced});

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Icon(synced ? Icons.cloud_done_outlined : Icons.cloud_outlined,
          color: synced ? AppColors.safe : AppColors.textMuted, size: 17),
      const SizedBox(width: 6),
      Text('Cloud Sync: ${synced ? "ON" : "OFF"}',
          style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: synced ? AppColors.safe : AppColors.textMuted)),
    ]);
  }
}

// ── Clock display ────────────────────────────────────────────────────────────

class _ClockDisplay extends StatelessWidget {
  final DateTime now;
  const _ClockDisplay({required this.now});

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      const Icon(Icons.calendar_today_outlined,
          color: AppColors.textSecondary, size: 16),
      const SizedBox(width: 8),
      Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(DateFormat('hh:mm:ss a').format(now),
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  fontFeatures: [FontFeature.tabularFigures()])),
          Text(DateFormat('d MMM yyyy').format(now),
              style: TextStyle(fontSize: 10, color: AppColors.textSecondary)),
        ],
      ),
    ]);
  }
}
