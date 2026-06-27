/// alarm_banner.dart – Slide-in alarm notification banner.
/// Appears at the top of the content area when an active alarm fires.
/// Auto-dismisses after 8 s; can also be swiped or tapped to dismiss.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/telemetry.dart';
import '../providers/dashboard_provider.dart';
import '../theme/app_theme.dart';

class AlarmBanner extends StatelessWidget {
  const AlarmBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    final show     = provider.showAlarmBanner;
    final level    = provider.alarmBannerLevel;
    final msg      = provider.alarmBannerMessage;

    Color bannerColor;
    IconData bannerIcon;
    switch (level) {
      case AlarmLevel.ALARM:
        bannerColor = AppColors.alarm;
        bannerIcon  = Icons.error_rounded;
        break;
      case AlarmLevel.WARNING:
        bannerColor = AppColors.warning;
        bannerIcon  = Icons.warning_rounded;
        break;
      case AlarmLevel.FAULT:
        bannerColor = AppColors.fault;
        bannerIcon  = Icons.report_problem_rounded;
        break;
      default:
        bannerColor = AppColors.safe;
        bannerIcon  = Icons.check_circle_rounded;
    }

    return AnimatedSlide(
      offset: show ? Offset.zero : const Offset(0, -1),
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeOutCubic,
      child: AnimatedOpacity(
        opacity: show ? 1.0 : 0.0,
        duration: const Duration(milliseconds: 200),
        child: show
            ? _BannerBody(
                color:  bannerColor,
                icon:   bannerIcon,
                msg:    msg,
                onDismiss: provider.dismissAlarmBanner,
              )
            : const SizedBox.shrink(),
      ),
    );
  }
}

class _BannerBody extends StatelessWidget {
  final Color color;
  final IconData icon;
  final String msg;
  final VoidCallback onDismiss;

  const _BannerBody({
    required this.color,
    required this.icon,
    required this.msg,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onDismiss,
      child: Container(
        margin: const EdgeInsets.fromLTRB(12, 6, 12, 0),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.6), width: 1.5),
          boxShadow: [BoxShadow(color: color.withOpacity(0.2), blurRadius: 12)],
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Text(msg,
                  style: TextStyle(
                      color: color,
                      fontSize: 13,
                      fontWeight: FontWeight.w600)),
            ),
            Icon(Icons.close_rounded, color: color.withOpacity(0.6), size: 18),
          ],
        ),
      ),
    );
  }
}
