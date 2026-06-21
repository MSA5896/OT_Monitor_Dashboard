import 'package:flutter/material.dart';
import '../models/telemetry.dart';

/// "Clinical Light" palette — grounded in healthcare-UX research and the
/// IEC 60601-1-8 medical alarm colour standard:
///   red = critical/high-priority, amber = warning/medium, green = normal,
///   cyan = low-priority / informational (used here for sensor FAULT).
/// Light, calm base for bright OT / ward environments; strong colours are
/// reserved strictly for alarm states.
class AppColors {
  // Base surfaces
  static const background = Color(0xFFF4F7FB); // pale blue-grey
  static const surface = Color(0xFFFFFFFF); // white cards
  static const surfaceAlt = Color(0xFFEEF3F9); // subtle panels / table striping
  static const border = Color(0xFFE2E8F0);

  // Text
  static const textPrimary = Color(0xFF1B2A41); // deep slate-navy
  static const textSecondary = Color(0xFF5A6B82);
  static const textMuted = Color(0xFF93A1B5);

  // Brand accent
  static const accent = Color(0xFF0E7C86); // teal
  static const accentDark = Color(0xFF0A5C64);

  // IEC alarm semantics
  static const normal = Color(0xFF2E9E5B); // green
  static const warning = Color(0xFFE6A100); // amber
  static const alarm = Color(0xFFD32F2F); // red
  static const fault = Color(0xFF00838F); // cyan (IEC low-priority/info)

  // Muted, clinical per-parameter chart hues
  static const temp = Color(0xFFE2683C);
  static const hum = Color(0xFF2E86C1);
  static const pm1 = Color(0xFF7E57C2);
  static const pm25 = Color(0xFFEF6C57);
  static const pm10 = Color(0xFFAD6A6C);
  static const co2 = Color(0xFF2E9E5B);
  static const voc = Color(0xFF8D6E63);
}

Color alarmColor(AlarmLevel level) {
  switch (level) {
    case AlarmLevel.alarm:
      return AppColors.alarm;
    case AlarmLevel.warning:
      return AppColors.warning;
    case AlarmLevel.fault:
      return AppColors.fault;
    case AlarmLevel.normal:
      return AppColors.normal;
  }
}

String alarmLabel(AlarmLevel level) {
  switch (level) {
    case AlarmLevel.alarm:
      return 'CRITICAL';
    case AlarmLevel.warning:
      return 'WARNING';
    case AlarmLevel.fault:
      return 'FAULT';
    case AlarmLevel.normal:
      return 'NORMAL';
  }
}

/// System-level status banner colour (SAFE / WARNING / ALERT / FAULT).
Color systemStatusColor(String status) {
  switch (status.toUpperCase()) {
    case 'ALERT':
      return AppColors.alarm;
    case 'WARNING':
      return AppColors.warning;
    case 'FAULT':
      return AppColors.fault;
    default:
      return AppColors.normal;
  }
}

String systemStatusLabel(String status) {
  switch (status.toUpperCase()) {
    case 'ALERT':
      return 'CRITICAL ALERT';
    case 'WARNING':
      return 'WARNING';
    case 'FAULT':
      return 'SENSOR FAULT';
    default:
      return 'ALL SAFE';
  }
}

ThemeData buildClinicalTheme() {
  final base = ThemeData.light(useMaterial3: true);
  final scheme = base.colorScheme.copyWith(
    primary: AppColors.accent,
    onPrimary: Colors.white,
    surface: AppColors.surface,
    onSurface: AppColors.textPrimary,
    error: AppColors.alarm,
  );
  return base.copyWith(
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: scheme,
    dividerColor: AppColors.border,
    textTheme: base.textTheme.apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    ),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
    ),
  );
}
