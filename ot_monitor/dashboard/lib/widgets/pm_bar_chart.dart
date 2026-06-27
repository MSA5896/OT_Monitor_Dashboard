/// pm_bar_chart.dart – Horizontal progress bars for PM1, PM2.5, PM10.
/// Bar fills proportionally against the configured alarm threshold.
/// Color-coded per parameter with alarm state glow.

import 'package:flutter/material.dart';
import '../models/telemetry.dart';
import '../theme/app_theme.dart';

class PmBarChart extends StatelessWidget {
  final double? pm1;
  final double? pm25;
  final double? pm10;
  final AlarmLevel pm1Level;
  final AlarmLevel pm25Level;
  final AlarmLevel pm10Level;

  // Reference maxes for bar fill (100%)
  static const double _pm1Max  = 100.0;
  static const double _pm25Max = 100.0;
  static const double _pm10Max = 150.0;

  const PmBarChart({
    super.key,
    this.pm1,
    this.pm25,
    this.pm10,
    this.pm1Level  = AlarmLevel.NORMAL,
    this.pm25Level = AlarmLevel.NORMAL,
    this.pm10Level = AlarmLevel.NORMAL,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Title ───────────────────────────────────────────────────────
          Row(
            children: [
              Icon(Icons.air_rounded,
                  color: AppColors.textSecondary, size: 16),
              const SizedBox(width: 6),
              Text('Air Contaminant Levels',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge!
                      .copyWith(fontSize: 14, color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 16),

          // ── Bars ────────────────────────────────────────────────────────
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _PmRow(
                  label: 'PM1',
                  value: pm1,
                  maxVal: _pm1Max,
                  barColor: AppColors.pm1Color,
                  unit: 'µg/m³',
                  level: pm1Level,
                ),
                _PmRow(
                  label: 'PM2.5',
                  value: pm25,
                  maxVal: _pm25Max,
                  barColor: AppColors.pm25Color,
                  unit: 'µg/m³',
                  level: pm25Level,
                ),
                _PmRow(
                  label: 'PM10',
                  value: pm10,
                  maxVal: _pm10Max,
                  barColor: AppColors.pm10Color,
                  unit: 'µg/m³',
                  level: pm10Level,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PmRow extends StatelessWidget {
  final String label;
  final double? value;
  final double maxVal;
  final Color barColor;
  final String unit;
  final AlarmLevel level;

  const _PmRow({
    required this.label,
    required this.value,
    required this.maxVal,
    required this.barColor,
    required this.unit,
    required this.level,
  });

  Color get _alarmColor {
    switch (level) {
      case AlarmLevel.WARNING: return AppColors.warning;
      case AlarmLevel.ALARM:   return AppColors.alarm;
      case AlarmLevel.FAULT:   return AppColors.fault;
      case AlarmLevel.NORMAL:  return barColor;
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool faulty = level == AlarmLevel.FAULT;
    final double fraction =
        faulty ? 0 : ((value ?? 0).clamp(0.0, maxVal) / maxVal);
    final String valText = faulty
        ? '—'
        : value != null
            ? '${value!.toStringAsFixed(0)} $unit'
            : '— $unit';

    return Row(
      children: [
        // Label
        SizedBox(
          width: 44,
          child: Text(label,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary)),
        ),

        // Bar
        Expanded(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            height: 18,
            decoration: BoxDecoration(
              color: AppColors.background,
              borderRadius: BorderRadius.circular(9),
              border: Border.all(
                  color: _alarmColor.withOpacity(0.3), width: 1),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: fraction,
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(9),
                  color: _alarmColor,
                  boxShadow: [
                    BoxShadow(
                      color: _alarmColor.withOpacity(0.4),
                      blurRadius: 6,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),

        // Value text
        SizedBox(
          width: 88,
          child: Padding(
            padding: const EdgeInsets.only(left: 8),
            child: Text(
              valText,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: _alarmColor,
              ),
              textAlign: TextAlign.right,
            ),
          ),
        ),
      ],
    );
  }
}
