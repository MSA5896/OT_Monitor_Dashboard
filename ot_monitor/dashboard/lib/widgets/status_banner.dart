import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Wide system-status banner shown at the top of the Monitor screen.
/// Colour + label roll up the worst active parameter (SAFE/WARNING/ALERT/FAULT).
class StatusBanner extends StatelessWidget {
  final String systemStatus;
  final int activeAlarmCount;

  const StatusBanner({
    super.key,
    required this.systemStatus,
    required this.activeAlarmCount,
  });

  @override
  Widget build(BuildContext context) {
    final color = systemStatusColor(systemStatus);
    final label = systemStatusLabel(systemStatus);
    final safe = systemStatus.toUpperCase() == 'SAFE';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Row(
        children: [
          Icon(
            safe ? Icons.verified_rounded : Icons.warning_amber_rounded,
            color: color,
            size: 26,
          ),
          const SizedBox(width: 12),
          Text(
            label,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.5,
              color: color,
            ),
          ),
          const Spacer(),
          if (!safe)
            Text(
              activeAlarmCount == 1
                  ? '1 active condition'
                  : '$activeAlarmCount active conditions',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
        ],
      ),
    );
  }
}
