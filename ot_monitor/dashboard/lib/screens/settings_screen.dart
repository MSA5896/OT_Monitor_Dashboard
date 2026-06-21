import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/dashboard_provider.dart';
import '../services/app_config.dart';
import '../theme/app_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _host =
      TextEditingController(text: AppConfig.host);
  late final TextEditingController _port =
      TextEditingController(text: AppConfig.port.toString());
  final _user = TextEditingController();
  final _pass = TextEditingController();

  Map<String, dynamic>? _thresholds;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadThresholds();
  }

  @override
  void dispose() {
    _host.dispose();
    _port.dispose();
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _loadThresholds() async {
    try {
      final api = context.read<DashboardProvider>().api;
      final t = await api.getThresholds();
      if (mounted) setState(() => _thresholds = t);
    } catch (_) {/* shown only when reachable */}
  }

  void _snack(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _saveConnection() async {
    final port = int.tryParse(_port.text.trim()) ?? AppConfig.port;
    await AppConfig.save(_host.text, port);
    if (!mounted) return;
    context.read<DashboardProvider>().reconnect();
    _snack('Connection updated — reconnecting to ${AppConfig.wsUrl}');
  }

  Future<void> _login() async {
    setState(() => _busy = true);
    final api = context.read<DashboardProvider>().api;
    final ok = await api.login(_user.text.trim(), _pass.text);
    setState(() => _busy = false);
    if (ok) {
      _pass.clear();
      _snack('Signed in as ${api.username} (${api.role}).');
      _loadThresholds();
    } else {
      _snack('Login failed — check username/password.');
    }
  }

  Future<void> _logout() async {
    await context.read<DashboardProvider>().api.logout();
    if (mounted) setState(() {});
    _snack('Signed out.');
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<DashboardProvider>().api;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Settings',
              style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary)),
          const SizedBox(height: 18),

          // ── Connection ──
          _Section(
            title: 'BACKEND CONNECTION',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: _host,
                        decoration: const InputDecoration(
                            labelText: 'Host', border: OutlineInputBorder()),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _port,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: 'Port', border: OutlineInputBorder()),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: _saveConnection,
                  style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
                  child: const Text('Save & reconnect'),
                ),
              ],
            ),
          ),

          // ── Account ──
          _Section(
            title: 'ACCOUNT',
            child: api.isLoggedIn
                ? Row(
                    children: [
                      const Icon(Icons.account_circle_rounded,
                          color: AppColors.accent, size: 28),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Signed in as ${api.username}  ·  role: ${api.role}',
                          style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary),
                        ),
                      ),
                      OutlinedButton(
                          onPressed: _logout, child: const Text('Sign out')),
                    ],
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Sign in for admin actions (acknowledge alarms, change settings).',
                        style: TextStyle(
                            fontSize: 13, color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _user,
                              decoration: const InputDecoration(
                                  labelText: 'Username',
                                  border: OutlineInputBorder()),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextField(
                              controller: _pass,
                              obscureText: true,
                              onSubmitted: (_) => _login(),
                              decoration: const InputDecoration(
                                  labelText: 'Password',
                                  border: OutlineInputBorder()),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      FilledButton(
                        onPressed: _busy ? null : _login,
                        style: FilledButton.styleFrom(
                            backgroundColor: AppColors.accent),
                        child: _busy
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white))
                            : const Text('Sign in'),
                      ),
                    ],
                  ),
          ),

          // ── Thresholds (read-only) ──
          _Section(
            title: 'ALARM THRESHOLDS  (read-only)',
            child: _thresholds == null
                ? const Text('Thresholds unavailable (backend not reachable).',
                    style: TextStyle(color: AppColors.textMuted))
                : Column(
                    children: _thresholds!.entries
                        .where((e) => e.value is Map)
                        .map((e) => _thresholdRow(
                            e.key, (e.value as Map).cast<String, dynamic>()))
                        .toList(),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _thresholdRow(String param, Map<String, dynamic> t) {
    String g(String k) => t[k] == null ? '–' : '${t[k]}';
    final unit = t['unit']?.toString() ?? '';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Text(
              param.replaceAll('_', ' ').toUpperCase(),
              style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                  color: AppColors.textPrimary),
            ),
          ),
          Expanded(
            flex: 3,
            child: Text(
              'warn ${g('warning_low')}–${g('warning_high')}   '
              'alarm ${g('alarm_low')}–${g('alarm_high')} $unit',
              style: const TextStyle(
                  fontSize: 12, color: AppColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final Widget child;
  const _Section({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
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
          child,
        ],
      ),
    );
  }
}
