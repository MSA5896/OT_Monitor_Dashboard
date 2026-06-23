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
          // Faded MSA logo watermark — very low opacity so the white logo
          // background disappears into the light gradient, leaving a faint mark.
          Positioned(
            right: -30,
            bottom: -20,
            child: Opacity(
              opacity: 0.05,
              child: Image.asset(
                'assets/logo.png',
                width: 520,
                fit: BoxFit.contain,
              ),
            ),
          ),
          child,
        ],
      ),
    );
  }
}
