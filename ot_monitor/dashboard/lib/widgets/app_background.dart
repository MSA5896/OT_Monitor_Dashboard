import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Full-screen bluish gradient background with a faint, gradient-faded logo
/// watermark. The watermark is a placeholder until the real (bluish) logo asset
/// is supplied — drop it into assets/ and swap the Icon for an Image here.
class AppBackground extends StatelessWidget {
  final Widget child;
  const AppBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(gradient: AppColors.backgroundGradient),
      child: Stack(
        children: [
          // Faded logo watermark (placeholder). Large, very low opacity, bottom-right.
          Positioned(
            right: -40,
            bottom: -30,
            child: ShaderMask(
              shaderCallback: (rect) => LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppColors.accent.withValues(alpha: 0.06),
                  AppColors.accent.withValues(alpha: 0.0),
                ],
              ).createShader(rect),
              blendMode: BlendMode.srcIn,
              child: const Icon(Icons.monitor_heart_rounded, size: 360),
            ),
          ),
          child,
        ],
      ),
    );
  }
}
