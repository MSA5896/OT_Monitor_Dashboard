import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/dashboard_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';
import 'alarms_screen.dart';
import 'history_screen.dart';
import 'settings_screen.dart';

enum _AdminDest { sensors, locations, alarms, history, account }

/// Admin window: opened after the floating gear → login. Has a PERMANENT left
/// sidebar (not an overlay) from which admins configure everything.
class AdminShell extends StatefulWidget {
  final VoidCallback onExit; // return to Monitor (keep session)
  final VoidCallback onSignOut; // logout + return to Monitor

  const AdminShell({super.key, required this.onExit, required this.onSignOut});

  @override
  State<AdminShell> createState() => _AdminShellState();
}

class _AdminShellState extends State<AdminShell> {
  _AdminDest _dest = _AdminDest.sensors;

  static const _meta = {
    _AdminDest.sensors: ('Sensors', Icons.sensors_rounded),
    _AdminDest.locations: ('Locations', Icons.location_on_rounded),
    _AdminDest.alarms: ('Alarms', Icons.notifications_active_rounded),
    _AdminDest.history: ('History', Icons.show_chart_rounded),
    _AdminDest.account: ('Account', Icons.manage_accounts_rounded),
  };

  Widget _panel() {
    switch (_dest) {
      case _AdminDest.sensors:
        return const SensorsPanel();
      case _AdminDest.locations:
        return const LocationsPanel();
      case _AdminDest.alarms:
        return const AlarmsScreen();
      case _AdminDest.history:
        return const HistoryScreen();
      case _AdminDest.account:
        return const AccountPanel();
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<DashboardProvider>().api;
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AppBackground(
        child: SafeArea(
          child: Row(
            children: [
              _sidebar(),
              Expanded(
                child: Column(
                  children: [
                    _topBar(api.username ?? 'admin'),
                    Expanded(child: _panel()),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _topBar(String username) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 22),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.85),
        border: const Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          Text(_meta[_dest]!.$1,
              style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary)),
          const Spacer(),
          const Icon(Icons.verified_user_rounded,
              size: 18, color: AppColors.accent),
          const SizedBox(width: 6),
          Text('Signed in as $username',
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary)),
        ],
      ),
    );
  }

  Widget _sidebar() {
    return Container(
      width: 232,
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(right: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 10),
            child: Row(
              children: [
                Image.asset('assets/logo.png', height: 34),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text('Admin\nConsole',
                      style: TextStyle(
                          fontSize: 12,
                          height: 1.1,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textSecondary)),
                ),
              ],
            ),
          ),
          const Divider(height: 8, indent: 14, endIndent: 14),
          const SizedBox(height: 6),
          for (final d in _AdminDest.values) _navItem(d),
          const Spacer(),
          const Divider(height: 8, indent: 14, endIndent: 14),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 6, 10, 6),
            child: TextButton.icon(
              onPressed: widget.onExit,
              icon: const Icon(Icons.monitor_rounded, size: 18),
              label: const Text('Back to Monitor'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.accent,
                alignment: Alignment.centerLeft,
                minimumSize: const Size.fromHeight(40),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 0, 10, 12),
            child: TextButton.icon(
              onPressed: widget.onSignOut,
              icon: const Icon(Icons.logout_rounded, size: 18),
              label: const Text('Sign out'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.alarm,
                alignment: Alignment.centerLeft,
                minimumSize: const Size.fromHeight(40),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _navItem(_AdminDest d) {
    final selected = d == _dest;
    final meta = _meta[d]!;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      child: Material(
        color: selected
            ? AppColors.accent.withValues(alpha: 0.12)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => setState(() => _dest = d),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Icon(meta.$2,
                    size: 20,
                    color:
                        selected ? AppColors.accent : AppColors.textSecondary),
                const SizedBox(width: 12),
                Text(meta.$1,
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: selected
                            ? AppColors.accent
                            : AppColors.textPrimary)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
