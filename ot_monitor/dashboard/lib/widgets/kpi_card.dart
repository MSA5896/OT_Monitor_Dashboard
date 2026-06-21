import 'package:flutter/material.dart';

import '../models/telemetry.dart';
import '../theme/app_theme.dart';

/// A single environmental parameter tile: label, live value, unit, and an
/// IEC-coloured status chip. A thin top accent bar carries the parameter hue;
/// the card border/chip reflect the current alarm level.
class KpiCard extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color accent;
  final double? value;
  final String unit;
  final int decimals;
  final AlarmLevel level;

  const KpiCard({
    super.key,
    required this.label,
    required this.icon,
    required this.accent,
    required this.value,
    required this.unit,
    required this.level,
    this.decimals = 1,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = alarmColor(level);
    final hasValue = value != null;
    final valueText = hasValue ? value!.toStringAsFixed(decimals) : '—';
    final isAlarm = level == AlarmLevel.alarm;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: level == AlarmLevel.normal
              ? AppColors.border
              : statusColor.withValues(alpha: 0.55),
          width: level == AlarmLevel.normal ? 1 : 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF1B2A41).withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            height: 4,
            decoration: BoxDecoration(
              color: accent,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(13)),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(icon, size: 18, color: accent),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          label,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                            color: AppColors.textSecondary,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      Text(
                        valueText,
                        style: TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.w800,
                          color: hasValue ? AppColors.textPrimary : AppColors.textMuted,
                          height: 1,
                        ),
                      ),
                      const SizedBox(width: 5),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 3),
                        child: Text(
                          unit,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ),
                    ],
                  ),
                  _StatusChip(level: level, color: statusColor, pulse: isAlarm),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final AlarmLevel level;
  final Color color;
  final bool pulse;
  const _StatusChip({required this.level, required this.color, required this.pulse});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            alarmLabel(level),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
