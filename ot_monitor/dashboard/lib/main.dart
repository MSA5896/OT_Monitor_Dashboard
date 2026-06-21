import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'providers/dashboard_provider.dart';
import 'services/api_service.dart';
import 'services/app_config.dart';
import 'services/websocket_service.dart';
import 'screens/alarms_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/history_screen.dart';
import 'screens/settings_screen.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.load();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => DashboardProvider(WebSocketService(), ApiService()),
      child: MaterialApp(
        title: 'OT Infection Monitor',
        debugShowCheckedModeBanner: false,
        theme: buildClinicalTheme(),
        home: const AppShell(),
      ),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;

  Widget _screen() {
    switch (_index) {
      case 1:
        return const AlarmsScreen();
      case 2:
        return const HistoryScreen();
      case 3:
        return const SettingsScreen();
      default:
        return const DashboardScreen();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Row(
          children: [
            _NavRail(
              index: _index,
              onSelect: (i) => setState(() => _index = i),
            ),
            Expanded(
              child: Column(
                children: [
                  const _HeaderBar(),
                  Expanded(child: _screen()),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavRail extends StatelessWidget {
  final int index;
  final ValueChanged<int> onSelect;
  const _NavRail({required this.index, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 76,
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(right: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        children: [
          const SizedBox(height: 18),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.monitor_heart_rounded,
                color: AppColors.accent, size: 24),
          ),
          const SizedBox(height: 24),
          _navItem(0, Icons.dashboard_rounded, 'Monitor'),
          _navItem(1, Icons.notifications_active_rounded, 'Alarms'),
          _navItem(2, Icons.show_chart_rounded, 'History'),
          const Spacer(),
          _navItem(3, Icons.settings_rounded, 'Settings'),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _navItem(int i, IconData icon, String label) {
    final selected = i == index;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Tooltip(
        message: label,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => onSelect(i),
          child: Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: selected
                  ? AppColors.accent.withValues(alpha: 0.12)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon,
                color: selected ? AppColors.accent : AppColors.textMuted,
                size: 24),
          ),
        ),
      ),
    );
  }
}

class _HeaderBar extends StatefulWidget {
  const _HeaderBar();

  @override
  State<_HeaderBar> createState() => _HeaderBarState();
}

class _HeaderBarState extends State<_HeaderBar> {
  late Timer _clock;
  DateTime _now = DateTime.now();

  @override
  void initState() {
    super.initState();
    _clock = Timer.periodic(
        const Duration(seconds: 1), (_) => setState(() => _now = DateTime.now()));
  }

  @override
  void dispose() {
    _clock.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    final payload = provider.latest;
    final otName = payload?.otName ?? 'Operating Theatre';
    final otId = payload?.otId ?? '';

    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                otName,
                style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary),
              ),
              Text(
                otId.isEmpty ? 'OT Infection Monitoring System' : 'ID: $otId',
                style: const TextStyle(
                    fontSize: 11, color: AppColors.textMuted),
              ),
            ],
          ),
          const Spacer(),
          if (payload != null) ...[
            _systemPill(payload.systemStatus),
            const SizedBox(width: 14),
          ],
          _connectionBadge(provider.connection),
          const SizedBox(width: 18),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                DateFormat('HH:mm:ss').format(_now),
                style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary),
              ),
              Text(
                DateFormat('EEE, dd MMM').format(_now),
                style: const TextStyle(
                    fontSize: 11, color: AppColors.textMuted),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _systemPill(String status) {
    final color = systemStatusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 7),
          Text(
            systemStatusLabel(status),
            style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.w700, color: color),
          ),
        ],
      ),
    );
  }

  Widget _connectionBadge(WsState state) {
    late final Color color;
    late final String label;
    late final IconData icon;
    switch (state) {
      case WsState.connected:
        color = AppColors.normal;
        label = 'Live';
        icon = Icons.wifi_rounded;
        break;
      case WsState.connecting:
        color = AppColors.warning;
        label = 'Connecting';
        icon = Icons.wifi_find_rounded;
        break;
      case WsState.disconnected:
        color = AppColors.alarm;
        label = 'Offline';
        icon = Icons.wifi_off_rounded;
        break;
    }
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 6),
        Text(label,
            style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.w600, color: color)),
      ],
    );
  }
}
