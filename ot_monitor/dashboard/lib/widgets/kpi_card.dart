import 'package:flutter/material.dart';

import '../models/telemetry.dart';
import '../theme/app_theme.dart';

/// Compact environmental-parameter tile sized to fill its grid cell: a coloured
/// accent strip, label, large value + unit, and an IEC-coloured status chip.
/// Designed for an at-a-glance, no-scroll 9.7" panel (two full rows of tiles).
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
    final isNormal = level == AlarmLevel.normal;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isNormal ? AppColors.border : statusColor.withValues(alpha: 0.6),
          width: isNormal ? 1 : 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.accent.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            width: 5,
            decoration: BoxDecoration(
              color: accent,
              borderRadius: const BorderRadius.horizontal(left: Radius.circular(11)),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(icon, size: 15, color: accent),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          label,
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.8,
                            color: AppColors.textSecondary,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          valueText,
                          style: TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                            color: hasValue
                                ? AppColors.textPrimary
                                : AppColors.textMuted,
                            height: 1,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          unit,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration:
                              BoxDecoration(color: statusColor, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 5),
                        Text(
                          alarmLabel(level),
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.4,
                            color: statusColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
