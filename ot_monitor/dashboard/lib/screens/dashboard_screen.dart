import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/telemetry.dart';
import '../providers/dashboard_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/kpi_card.dart';
import '../widgets/trend_chart.dart';

/// Public Monitor screen. Fixed, no-scroll layout for a 9.7" panel:
/// location selector bar → two full-width rows of parameter tiles →
/// a full-width live trend graph. Battery lives in the header; detailed
/// per-sensor / threshold "slider" data lives in admin Settings.
class DashboardScreen extends StatefulWidget {
  /// Opens the styled location picker overlay (from the location bar tap).
  final VoidCallback onPickLocation;
  const DashboardScreen({super.key, required this.onPickLocation});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  String _trendKey = 'pm25_ugm3';

  static const _trendOptions = {
    'temperature_c': ('Temperature', '°C', AppColors.temp),
    'relative_humidity_pct': ('Humidity', '%', AppColors.hum),
    'pm25_ugm3': ('PM2.5', 'µg/m³', AppColors.pm25),
    'co2_ppm': ('CO₂', 'ppm', AppColors.co2),
  };

  double? _valueForKey(OTData d, String key) {
    switch (key) {
      case 'temperature_c':
        return d.temperatureC;
      case 'relative_humidity_pct':
        return d.relativeHumidityPct;
      case 'pm25_ugm3':
        return d.pm25;
      case 'co2_ppm':
        return d.co2Ppm;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DashboardProvider>();
    final payload = provider.latest;

    if (payload == null) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: AppColors.accent),
            SizedBox(height: 16),
            Text('Connecting to monitor…',
                style: TextStyle(color: AppColors.textSecondary)),
          ],
        ),
      );
    }

    final d = payload.data;
    final cards = <Widget>[
      KpiCard(
          label: 'TEMPERATURE',
          icon: Icons.thermostat_rounded,
          accent: AppColors.temp,
          value: d.temperatureC,
          unit: '°C',
          level: payload.levelFor('temperature_c')),
      KpiCard(
          label: 'HUMIDITY',
          icon: Icons.water_drop_rounded,
          accent: AppColors.hum,
          value: d.relativeHumidityPct,
          unit: '%',
          level: payload.levelFor('relative_humidity_pct')),
      KpiCard(
          label: 'PM1.0',
          icon: Icons.blur_on_rounded,
          accent: AppColors.pm1,
          value: d.pm1,
          unit: 'µg/m³',
          level: payload.levelFor('pm1_ugm3')),
      KpiCard(
          label: 'PM2.5',
          icon: Icons.blur_on_rounded,
          accent: AppColors.pm25,
          value: d.pm25,
          unit: 'µg/m³',
          level: payload.levelFor('pm25_ugm3')),
      KpiCard(
          label: 'PM10',
          icon: Icons.blur_on_rounded,
          accent: AppColors.pm10,
          value: d.pm10,
          unit: 'µg/m³',
          level: payload.levelFor('pm10_ugm3')),
      KpiCard(
          label: 'CO₂',
          icon: Icons.co2_rounded,
          accent: AppColors.co2,
          value: d.co2Ppm,
          unit: 'ppm',
          level: payload.levelFor('co2_ppm'),
          decimals: 0),
      KpiCard(
          label: 'VOC',
          icon: Icons.air_rounded,
          accent: AppColors.voc,
          value: d.vocPpb,
          unit: 'ppb',
          level: payload.levelFor('voc_ppb'),
          decimals: 0),
      KpiCard(
          label: 'DIFF PRESSURE',
          icon: Icons.compare_arrows_rounded,
          accent: AppColors.accent,
          value: d.diffPressurePa,
          unit: 'Pa',
          level: payload.levelFor('diff_pressure_pa')),
    ];

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: LayoutBuilder(
        builder: (context, c) {
          const locBar = 46.0;
          const gap = 12.0;
          final remaining = c.maxHeight - locBar - gap * 2;
          final cardsH = remaining * 0.46;
          final graphH = remaining - cardsH;
          final rowH = (cardsH - gap) / 2;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                height: locBar,
                child: _LocationBar(
                  provider: provider,
                  systemStatus: payload.systemStatus,
                  activeAlarms: payload.activeAlarms.length,
                  onPickLocation: widget.onPickLocation,
                ),
              ),
              const SizedBox(height: gap),
              SizedBox(
                height: cardsH,
                child: GridView.builder(
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 4,
                    crossAxisSpacing: gap,
                    mainAxisSpacing: gap,
                    mainAxisExtent: rowH,
                  ),
                  itemCount: cards.length,
                  itemBuilder: (_, i) => cards[i],
                ),
              ),
              const SizedBox(height: gap),
              SizedBox(height: graphH, child: _trendPanel(provider)),
            ],
          );
        },
      ),
    );
  }

  Widget _trendPanel(DashboardProvider provider) {
    final meta = _trendOptions[_trendKey]!;
    final spots = <FlSpot>[];
    final buffer = provider.liveBuffer;
    for (var i = 0; i < buffer.length; i++) {
      final v = _valueForKey(buffer[i].data, _trendKey);
      if (v != null) spots.add(FlSpot(i.toDouble(), v));
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: AppColors.accent.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('LIVE TREND',
                  style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.2,
                      color: AppColors.textSecondary)),
              const Spacer(),
              DropdownButton<String>(
                value: _trendKey,
                underline: const SizedBox.shrink(),
                isDense: true,
                borderRadius: BorderRadius.circular(10),
                style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w600,
                    fontSize: 13),
                items: _trendOptions.entries
                    .map((e) =>
                        DropdownMenuItem(value: e.key, child: Text(e.value.$1)))
                    .toList(),
                onChanged: (v) => setState(() => _trendKey = v ?? _trendKey),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Expanded(
            child: TrendChart(spots: spots, color: meta.$3, unit: meta.$2),
          ),
        ],
      ),
    );
  }
}

class _LocationBar extends StatelessWidget {
  final DashboardProvider provider;
  final String systemStatus;
  final int activeAlarms;
  final VoidCallback onPickLocation;
  const _LocationBar({
    required this.provider,
    required this.systemStatus,
    required this.activeAlarms,
    required this.onPickLocation,
  });

  @override
  Widget build(BuildContext context) {
    final color = systemStatusColor(systemStatus);
    final selected = provider.selectedLocation;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          // Tappable location selector → opens the styled picker overlay
          Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(9),
            child: InkWell(
              borderRadius: BorderRadius.circular(9),
              onTap: onPickLocation,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.location_on_rounded,
                        size: 18, color: AppColors.accent),
                    const SizedBox(width: 8),
                    Text(
                      selected != null
                          ? '${selected.name}  ·  ${selected.type}'
                          : 'Select location',
                      style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w800,
                          fontSize: 16),
                    ),
                    const SizedBox(width: 4),
                    const Icon(Icons.keyboard_arrow_down_rounded,
                        size: 20, color: AppColors.textSecondary),
                  ],
                ),
              ),
            ),
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  systemStatus.toUpperCase() == 'SAFE'
                      ? Icons.verified_rounded
                      : Icons.warning_amber_rounded,
                  size: 16,
                  color: color,
                ),
                const SizedBox(width: 7),
                Text(
                  systemStatusLabel(systemStatus) +
                      (activeAlarms > 0 ? '  ·  $activeAlarms active' : ''),
                  style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w700,
                      color: color),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
