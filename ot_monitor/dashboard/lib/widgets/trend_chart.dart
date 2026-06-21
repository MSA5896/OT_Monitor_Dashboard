import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Reusable line trend chart. Caller supplies already-built FlSpots
/// (x = relative seconds or index, y = value).
class TrendChart extends StatelessWidget {
  final List<FlSpot> spots;
  final Color color;
  final String unit;
  final double? minY;
  final double? maxY;

  const TrendChart({
    super.key,
    required this.spots,
    required this.color,
    required this.unit,
    this.minY,
    this.maxY,
  });

  @override
  Widget build(BuildContext context) {
    if (spots.length < 2) {
      return const Center(
        child: Text(
          'Collecting data…',
          style: TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
      );
    }

    final minX = spots.first.x;
    final maxX = spots.last.x;
    final ys = spots.map((s) => s.y);
    final dataMin = ys.reduce((a, b) => a < b ? a : b);
    final dataMax = ys.reduce((a, b) => a > b ? a : b);
    final lo = minY ?? (dataMin - (dataMax - dataMin).abs() * 0.15 - 1);
    final hi = maxY ?? (dataMax + (dataMax - dataMin).abs() * 0.15 + 1);

    return LineChart(
      LineChartData(
        minX: minX,
        maxX: maxX,
        minY: lo,
        maxY: hi,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: ((hi - lo) / 4).abs().clamp(0.1, double.infinity),
          getDrawingHorizontalLine: (_) =>
              const FlLine(color: AppColors.surfaceAlt, strokeWidth: 1),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: ((hi - lo) / 4).abs().clamp(0.1, double.infinity),
              getTitlesWidget: (value, meta) => Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Text(
                  value.toStringAsFixed(0),
                  style: const TextStyle(
                      color: AppColors.textMuted, fontSize: 10),
                ),
              ),
            ),
          ),
        ),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => AppColors.textPrimary,
            getTooltipItems: (items) => items
                .map((i) => LineTooltipItem(
                      '${i.y.toStringAsFixed(1)} $unit',
                      const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 12),
                    ))
                .toList(),
          ),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            curveSmoothness: 0.25,
            color: color,
            barWidth: 2.5,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: color.withValues(alpha: 0.12),
            ),
          ),
        ],
      ),
    );
  }
}
