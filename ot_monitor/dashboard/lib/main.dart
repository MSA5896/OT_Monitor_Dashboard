import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'providers/dashboard_provider.dart';
import 'services/api_service.dart';
import 'services/app_config.dart';
import 'services/websocket_service.dart';
import 'screens/admin_shell.dart';
import 'screens/dashboard_screen.dart';
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

/// Top-level switch between the public Monitor and the admin window.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _adminMode = false;

  Future<void> _enterAdmin() async {
    final provider = context.read<DashboardProvider>();
    if (!provider.isAdmin) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (_) => const _AdminLoginDialog(),
      );
      if (ok != true) return;
    }
    setState(() => _adminMode = true);
  }

  void _exitAdmin() => setState(() => _adminMode = false);

  void _signOut() {
    context.read<DashboardProvider>().api.logout();
    setState(() => _adminMode = false);
  }

  @override
  Widget build(BuildContext context) {
    final isAdmin = context.watch<DashboardProvider>().isAdmin;
    if (_adminMode && isAdmin) {
      return AdminShell(onExit: _exitAdmin, onSignOut: _signOut);
    }
    return MonitorShell(onOpenAdmin: _enterAdmin);
  }
}

/// Public monitor: header + live dashboard + a floating gear (admin) and a
/// location picker overlay opened from the top-left menu.
class MonitorShell extends StatefulWidget {
  final VoidCallback onOpenAdmin;
  const MonitorShell({super.key, required this.onOpenAdmin});

  @override
  State<MonitorShell> createState() => _MonitorShellState();
}

class _MonitorShellState extends State<MonitorShell> {
  bool _locOpen = false;

  void _toggleLoc() => setState(() => _locOpen = !_locOpen);
  void _closeLoc() => setState(() => _locOpen = false);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AppBackground(
        child: SafeArea(
          child: Stack(
            children: [
              Column(
                children: [
                  _MonitorHeader(onMenu: _toggleLoc),
                  Expanded(child: DashboardScreen(onPickLocation: _toggleLoc)),
                ],
              ),
              // Floating admin gear (bottom-right)
              Positioned(
                right: 22,
                bottom: 22,
                child: _GearButton(onTap: widget.onOpenAdmin),
              ),
              // Location picker overlay (opened from the top-left menu)
              if (_locOpen) ...[
                Positioned.fill(
                  child: GestureDetector(
                    onTap: _closeLoc,
                    child: Container(color: Colors.black.withValues(alpha: 0.18)),
                  ),
                ),
                _LocationOverlay(onClose: _closeLoc),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _GearButton extends StatelessWidget {
  final VoidCallback onTap;
  const _GearButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Admin settings',
      child: Material(
        color: AppColors.accent,
        shape: const CircleBorder(),
        elevation: 4,
        shadowColor: AppColors.accent.withValues(alpha: 0.5),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: const SizedBox(
            width: 56,
            height: 56,
            child: Icon(Icons.settings_rounded, color: Colors.white, size: 26),
          ),
        ),
      ),
    );
  }
}

/// Styled critical-location picker (replaces the old dropdown).
class _LocationOverlay extends StatelessWidget {
  final VoidCallback onClose;
  const _LocationOverlay({required this.onClose});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    return Align(
      alignment: Alignment.topLeft,
      child: Container(
        width: 320,
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
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 16, 12, 8),
              child: Row(
                children: [
                  const Icon(Icons.location_on_rounded,
                      color: AppColors.accent, size: 20),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text('Select Location',
                        style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary)),
                  ),
                  IconButton(
                    onPressed: onClose,
                    icon: const Icon(Icons.close_rounded, size: 20),
                    color: AppColors.textMuted,
                  ),
                ],
              ),
            ),
            const Divider(height: 1, color: AppColors.border),
            Flexible(
              child: ListView(
                shrinkWrap: true,
                padding: const EdgeInsets.all(10),
                children: provider.locations.map((loc) {
                  final selected = provider.selectedLocation?.id == loc.id;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Material(
                      color: selected
                          ? AppColors.accent.withValues(alpha: 0.10)
                          : AppColors.surfaceAlt,
                      borderRadius: BorderRadius.circular(12),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: () {
                          provider.selectLocation(loc);
                          onClose();
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          child: Row(
                            children: [
                              Container(
                                width: 38,
                                height: 38,
                                decoration: BoxDecoration(
                                  color: AppColors.accent.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Icon(Icons.meeting_room_rounded,
                                    color: AppColors.accent, size: 20),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(loc.name,
                                        style: const TextStyle(
                                            fontWeight: FontWeight.w700,
                                            fontSize: 14,
                                            color: AppColors.textPrimary)),
                                    Text('${loc.id}  ·  ${loc.type}',
                                        style: const TextStyle(
                                            fontSize: 11,
                                            color: AppColors.textMuted)),
                                  ],
                                ),
                              ),
                              if (selected)
                                const Icon(Icons.check_circle_rounded,
                                    color: AppColors.accent, size: 20),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 14),
              child: Text(
                'Admins can add locations from the gear → Locations.',
                style: TextStyle(
                    fontSize: 11, color: AppColors.textMuted.withValues(alpha: 1)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MonitorHeader extends StatefulWidget {
  final VoidCallback onMenu;
  const _MonitorHeader({required this.onMenu});

  @override
  State<_MonitorHeader> createState() => _MonitorHeaderState();
}

class _MonitorHeaderState extends State<_MonitorHeader> {
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
            tooltip: 'Locations',
          ),
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
          // Date + time on a single line
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(DateFormat('HH:mm:ss').format(_now),
                  style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary)),
              const SizedBox(width: 8),
              Text(DateFormat('EEE, dd MMM').format(_now),
                  style: const TextStyle(
                      fontSize: 12, color: AppColors.textMuted)),
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

/// Admin login popup shown when the floating gear is tapped (if not signed in).
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
