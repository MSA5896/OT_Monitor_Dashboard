/// header.dart – Top header bar: title, subtitle, heartbeat ECG line, logo area.

import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class DashboardHeader extends StatelessWidget {
  const DashboardHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(
          bottom: BorderSide(color: AppColors.border, width: 1),
        ),
      ),
      child: Row(
        children: [
          // ── Left: Title block ──────────────────────────────────────────
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  // Heartbeat icon pulse
                  Icon(Icons.monitor_heart_outlined,
                      color: AppColors.cyan, size: 22),
                  const SizedBox(width: 8),
                  RichText(
                    text: const TextSpan(
                      children: [
                        TextSpan(
                          text: 'OT ',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w700,
                            color: AppColors.cyan,
                            letterSpacing: 1,
                          ),
                        ),
                        TextSpan(
                          text: 'INFECTION MONITORING',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                'D A S H B O A R D',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textSecondary,
                  letterSpacing: 4,
                ),
              ),
            ],
          ),

          // ── Middle: ECG line decoration ───────────────────────────────
          const Expanded(child: _EcgDecoration()),

          // ── Right: Logo placeholder ────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.cyan.withOpacity(0.15),
                    border: Border.all(color: AppColors.cyan, width: 1.5),
                  ),
                  child: const Icon(Icons.medical_services,
                      color: AppColors.cyan, size: 16),
                ),
                const SizedBox(width: 10),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('MSA',
                        style: Theme.of(context).textTheme.titleLarge!.copyWith(
                            color: AppColors.cyan, fontSize: 18)),
                    Text('INTELLIGENT HEALTHCARE',
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall!
                            .copyWith(letterSpacing: 0.5)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Decorative ECG-style line in the header.
class _EcgDecoration extends StatelessWidget {
  const _EcgDecoration();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: CustomPaint(
        size: const Size(double.infinity, 28),
        painter: _EcgPainter(),
      ),
    );
  }
}

class _EcgPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.cyan.withOpacity(0.5)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final path = Path();
    final h = size.height;
    final w = size.width;
    final mid = h / 2;

    path.moveTo(0, mid);
    path.lineTo(w * 0.20, mid);
    path.lineTo(w * 0.25, mid - h * 0.2);
    path.lineTo(w * 0.30, mid + h * 0.4);
    path.lineTo(w * 0.35, mid - h * 0.9);
    path.lineTo(w * 0.40, mid + h * 0.3);
    path.lineTo(w * 0.45, mid - h * 0.1);
    path.lineTo(w * 0.50, mid);
    path.lineTo(w * 0.65, mid);
    path.lineTo(w * 0.70, mid - h * 0.15);
    path.lineTo(w * 0.75, mid + h * 0.3);
    path.lineTo(w * 0.80, mid - h * 0.7);
    path.lineTo(w * 0.85, mid + h * 0.2);
    path.lineTo(w * 0.88, mid);
    path.lineTo(w, mid);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}
