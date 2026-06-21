import 'package:flutter/material.dart';

import '../models/telemetry.dart';
import '../theme/app_theme.dart';

/// Particulate-matter breakdown: PM1 / PM2.5 / PM10 as horizontal-feel bars,
/// each scaled to its own display ceiling (config max_display) and coloured by
/// the backend alarm level for that fraction.
class PmBreakdown extends StatelessWidget {
  final double? pm1;
  final double? pm25;
  final double? pm10;
  final AlarmLevel pm1Level;
  final AlarmLevel pm25Level;
  final AlarmLevel pm10Level;

  const PmBreakdown({
    super.key,
    required this.pm1,
    required this.pm25,
    required this.pm10,
    required this.pm1Level,
    required this.pm25Level,
    required this.pm10Level,
  });

  @override
  Widget build(BuildContext context) {
    final rows = [
      _PmRow('PM1.0', pm1, 50, pm1Level),
      _PmRow('PM2.5', pm25, 75, pm25Level),
      _PmRow('PM10', pm10, 100, pm10Level),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: rows.map((r) => _bar(r)).toList(),
    );
  }

  Widget _bar(_PmRow r) {
    final color = alarmColor(r.level);
    final value = r.value ?? 0;
    final frac = (value / r.ceiling).clamp(0.0, 1.0);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                r.label,
                style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textSecondary),
              ),
              const Spacer(),
              Text(
                r.value != null ? '${r.value!.toStringAsFixed(1)} µg/m³' : '—',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: r.value != null ? color : AppColors.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: frac,
              minHeight: 9,
              backgroundColor: AppColors.surfaceAlt,
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
        ],
      ),
    );
  }
}

class _PmRow {
  final String label;
  final double? value;
  final double ceiling;
  final AlarmLevel level;
  _PmRow(this.label, this.value, this.ceiling, this.level);
}
