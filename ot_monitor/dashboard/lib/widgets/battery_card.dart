import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Backup-power tile: battery charge % with a fill bar, plus mains/battery
/// source. Battery colour uses standard UPS conventions (>50% green,
/// 20–50% amber, <20% red) — this is a device-health metric, not a medical
/// threshold, so it is coloured client-side.
class BatteryCard extends StatelessWidget {
  final double? batteryPct;
  final String powerSource; // MAINS | BATTERY | UNKNOWN

  const BatteryCard({
    super.key,
    required this.batteryPct,
    required this.powerSource,
  });

  Color get _battColor {
    final pct = batteryPct ?? 0;
    if (batteryPct == null) return AppColors.textMuted;
    if (pct < 20) return AppColors.alarm;
    if (pct < 50) return AppColors.warning;
    return AppColors.normal;
  }

  @override
  Widget build(BuildContext context) {
    final onMains = powerSource.toUpperCase() == 'MAINS';
    final onBattery = powerSource.toUpperCase() == 'BATTERY';
    final pct = batteryPct;
    final color = _battColor;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: onBattery ? AppColors.warning.withValues(alpha: 0.55) : AppColors.border,
          width: onBattery ? 1.5 : 1,
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
            decoration: const BoxDecoration(
              color: AppColors.accent,
              borderRadius: BorderRadius.vertical(top: Radius.circular(13)),
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
                      Icon(
                        onMains
                            ? Icons.power_rounded
                            : (onBattery
                                ? Icons.battery_charging_full_rounded
                                : Icons.battery_unknown_rounded),
                        size: 18,
                        color: AppColors.accent,
                      ),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'BACKUP POWER',
                          style: TextStyle(
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
                        pct != null ? pct.toStringAsFixed(0) : '—',
                        style: TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.w800,
                          color: pct != null ? AppColors.textPrimary : AppColors.textMuted,
                          height: 1,
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Padding(
                        padding: EdgeInsets.only(bottom: 3),
                        child: Text('%',
                            style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: AppColors.textMuted)),
                      ),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: pct == null ? 0 : (pct / 100).clamp(0, 1),
                          minHeight: 6,
                          backgroundColor: AppColors.surfaceAlt,
                          valueColor: AlwaysStoppedAnimation(color),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                        decoration: BoxDecoration(
                          color: (onBattery ? AppColors.warning : AppColors.normal)
                              .withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          onMains
                              ? 'ON MAINS'
                              : (onBattery ? 'ON BATTERY' : 'UNKNOWN'),
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                            color: onBattery ? AppColors.warning : AppColors.normal,
                          ),
                        ),
                      ),
                    ],
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
