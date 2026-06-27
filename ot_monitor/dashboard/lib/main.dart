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
import 'widgets/app_background.dart';

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

/// Nav destinations. Monitor + Settings are always present; Alarms + History
/// are revealed only after an admin signs in (via the Settings login popup).
enum NavDest { monitor, settings, alarms, history }

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  NavDest _dest = NavDest.monitor;
  bool _navOpen = false;

  Widget _screen() {
    switch (_dest) {
      case NavDest.settings:
        return const SettingsScreen();
      case NavDest.alarms:
        return const AlarmsScreen();
      case NavDest.history:
        return const HistoryScreen();
      case NavDest.monitor:
        return const DashboardScreen();
    }
  }

  Future<void> _onSelect(NavDest dest) async {
    final provider = context.read<DashboardProvider>();
    // Settings (and the admin-only sections) require an admin session.
    final needsAdmin = dest != NavDest.monitor;
    if (needsAdmin && !provider.isAdmin) {
      setState(() => _navOpen = false);
      final ok = await _showLoginDialog();
      if (ok != true) return;
    }
    setState(() {
      _dest = dest;
      _navOpen = false;
    });
  }

  Future<bool?> _showLoginDialog() {
    return showDialog<bool>(
      context: context,
      builder: (_) => const _AdminLoginDialog(),
    );
  }

  void _signOut() {
    final provider = context.read<DashboardProvider>();
    provider.api.logout();
    setState(() {
      _dest = NavDest.monitor;
      _navOpen = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AppBackground(
        child: SafeArea(
          child: Stack(
            children: [
              // Main content fills the full width; the nav floats above it.
              Column(
                children: [
                  _HeaderBar(onMenu: () => setState(() => _navOpen = !_navOpen)),
                  Expanded(child: _screen()),
                ],
              ),
              // Nav overlay (hidden by default; opened from the header menu).
              if (_navOpen) ...[
                Positioned.fill(
                  child: GestureDetector(
                    onTap: () => setState(() => _navOpen = false),
                    child: Container(color: Colors.black.withValues(alpha: 0.18)),
                  ),
                ),
                _NavOverlay(
                  current: _dest,
                  isAdmin: context.watch<DashboardProvider>().isAdmin,
                  onSelect: _onSelect,
                  onSignOut: _signOut,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Floating navigation panel — appears above the monitor content without
/// resizing it. Only Monitor + Settings until an admin is signed in.
class _NavOverlay extends StatelessWidget {
  final NavDest current;
  final bool isAdmin;
  final ValueChanged<NavDest> onSelect;
  final VoidCallback onSignOut;

  const _NavOverlay({
    required this.current,
    required this.isAdmin,
    required this.onSelect,
    required this.onSignOut,
  });

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topLeft,
      child: Container(
        width: 232,
        margin: const EdgeInsets.fromLTRB(10, 10, 0, 10),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
          boxShadow: [
            BoxShadow(
              color: AppColors.accent.withValues(alpha: 0.18),
              blurRadius: 24,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 14),
            _item(NavDest.monitor, Icons.dashboard_rounded, 'Monitor'),
            _item(NavDest.settings, Icons.settings_rounded, 'Settings',
                locked: !isAdmin),
            if (isAdmin) ...[
              const Divider(height: 18, indent: 14, endIndent: 14),
              _item(NavDest.alarms, Icons.notifications_active_rounded, 'Alarms'),
              _item(NavDest.history, Icons.show_chart_rounded, 'History'),
              const Divider(height: 18, indent: 14, endIndent: 14),
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
                child: TextButton.icon(
                  onPressed: onSignOut,
                  icon: const Icon(Icons.logout_rounded, size: 18),
                  label: const Text('Sign out'),
                  style: TextButton.styleFrom(foregroundColor: AppColors.alarm),
                ),
              ),
            ] else
              const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  Widget _item(NavDest dest, IconData icon, String label, {bool locked = false}) {
    final selected = dest == current;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Material(
        color: selected ? AppColors.accent.withValues(alpha: 0.12) : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => onSelect(dest),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Icon(icon,
                    size: 21,
                    color: selected ? AppColors.accent : AppColors.textSecondary),
                const SizedBox(width: 12),
                Text(label,
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: selected
                            ? AppColors.accent
                            : AppColors.textPrimary)),
                const Spacer(),
                if (locked)
                  const Icon(Icons.lock_outline_rounded,
                      size: 15, color: AppColors.textMuted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HeaderBar extends StatefulWidget {
  final VoidCallback onMenu;
  const _HeaderBar({required this.onMenu});

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
    final data = provider.latest?.data;

    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.85),
        border: const Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: widget.onMenu,
            icon: const Icon(Icons.menu_rounded, color: AppColors.textSecondary),
            tooltip: 'Menu',
          ),
          // MSA Intelligent Healthcare logo
          Image.asset('assets/logo.png', height: 38),
          const SizedBox(width: 12),
          Container(width: 1, height: 26, color: AppColors.border),
          const SizedBox(width: 12),
          const Text('OT Infection Monitor',
              style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary)),
          const Spacer(),
          _ConnectionBadge(state: provider.connection),
          const SizedBox(width: 16),
          _BatteryIndicator(
              pct: data?.batteryPct, source: data?.powerSource ?? 'UNKNOWN'),
          const SizedBox(width: 16),
          Container(width: 1, height: 26, color: AppColors.border),
          const SizedBox(width: 16),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(DateFormat('HH:mm:ss').format(_now),
                  style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary)),
              Text(DateFormat('EEE, dd MMM').format(_now),
                  style: const TextStyle(
                      fontSize: 10, color: AppColors.textMuted)),
            ],
          ),
        ],
      ),
    );
  }
}

class _BatteryIndicator extends StatelessWidget {
  final double? pct;
  final String source;
  const _BatteryIndicator({required this.pct, required this.source});

  @override
  Widget build(BuildContext context) {
    final onMains = source.toUpperCase() == 'MAINS';
    final onBattery = source.toUpperCase() == 'BATTERY';
    final p = pct;
    Color color;
    if (p == null) {
      color = AppColors.textMuted;
    } else if (p < 20) {
      color = AppColors.alarm;
    } else if (p < 50) {
      color = AppColors.warning;
    } else {
      color = AppColors.normal;
    }
    final icon = onMains
        ? Icons.power_rounded
        : (onBattery
            ? Icons.battery_charging_full_rounded
            : Icons.battery_unknown_rounded);

    return Tooltip(
      message: onMains
          ? 'On mains power'
          : (onBattery ? 'On backup battery' : 'Power source unknown'),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 5),
          Text(
            p != null ? '${p.toStringAsFixed(0)}%' : '—',
            style: TextStyle(
                fontSize: 14, fontWeight: FontWeight.w700, color: color),
          ),
          const SizedBox(width: 4),
          Text(onMains ? 'Mains' : (onBattery ? 'Batt' : ''),
              style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _ConnectionBadge extends StatelessWidget {
  final WsState state;
  const _ConnectionBadge({required this.state});

  @override
  Widget build(BuildContext context) {
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
      mainAxisSize: MainAxisSize.min,
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

/// Admin login popup shown when a protected section is opened.
class _AdminLoginDialog extends StatefulWidget {
  const _AdminLoginDialog();

  @override
  State<_AdminLoginDialog> createState() => _AdminLoginDialogState();
}

class _AdminLoginDialogState extends State<_AdminLoginDialog> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final api = context.read<DashboardProvider>().api;
    final ok = await api.login(_user.text.trim(), _pass.text);
    if (!mounted) return;
    if (ok) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _busy = false;
        _error = 'Invalid username or password.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Row(
        children: [
          Icon(Icons.admin_panel_settings_rounded, color: AppColors.accent),
          SizedBox(width: 10),
          Text('Admin sign in'),
        ],
      ),
      content: SizedBox(
        width: 340,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset('assets/logo.png', height: 52),
            const SizedBox(height: 14),
            const Text(
              'Settings and configuration are restricted to hospital admins.',
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _user,
              autofocus: true,
              decoration: const InputDecoration(
                  labelText: 'Username', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pass,
              obscureText: true,
              onSubmitted: (_) => _submit(),
              decoration: const InputDecoration(
                  labelText: 'Password', border: OutlineInputBorder()),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(_error!,
                  style: const TextStyle(color: AppColors.alarm, fontSize: 12)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _busy ? null : _submit,
          style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
          child: _busy
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white))
              : const Text('Sign in'),
        ),
      ],
    );
  }
}
