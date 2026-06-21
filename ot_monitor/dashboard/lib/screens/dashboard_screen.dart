import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/telemetry.dart';
import '../providers/dashboard_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/battery_card.dart';
import '../widgets/kpi_card.dart';
import '../widgets/pm_breakdown.dart';
import '../widgets/status_banner.dart';
import '../widgets/trend_chart.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

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
            Text('Connecting to OT monitor…',
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
        level: payload.levelFor('temperature_c'),
      ),
      KpiCard(
        label: 'HUMIDITY',
        icon: Icons.water_drop_rounded,
        accent: AppColors.hum,
        value: d.relativeHumidityPct,
        unit: '%',
        level: payload.levelFor('relative_humidity_pct'),
      ),
      KpiCard(
        label: 'PM1.0',
        icon: Icons.blur_on_rounded,
        accent: AppColors.pm1,
        value: d.pm1,
        unit: 'µg/m³',
        level: payload.levelFor('pm1_ugm3'),
      ),
      KpiCard(
        label: 'PM2.5',
        icon: Icons.blur_on_rounded,
        accent: AppColors.pm25,
        value: d.pm25,
        unit: 'µg/m³',
        level: payload.levelFor('pm25_ugm3'),
      ),
      KpiCard(
        label: 'PM10',
        icon: Icons.blur_on_rounded,
        accent: AppColors.pm10,
        value: d.pm10,
        unit: 'µg/m³',
        level: payload.levelFor('pm10_ugm3'),
      ),
      KpiCard(
        label: 'CO₂',
        icon: Icons.co2_rounded,
        accent: AppColors.co2,
        value: d.co2Ppm,
        unit: 'ppm',
        level: payload.levelFor('co2_ppm'),
        decimals: 0,
      ),
      KpiCard(
        label: 'VOC',
        icon: Icons.air_rounded,
        accent: AppColors.voc,
        value: d.vocPpb,
        unit: 'ppb',
        level: payload.levelFor('voc_ppb'),
        decimals: 0,
      ),
      KpiCard(
        label: 'DIFF PRESSURE',
        icon: Icons.compare_arrows_rounded,
        accent: AppColors.accent,
        value: d.diffPressurePa,
        unit: 'Pa',
        level: payload.levelFor('diff_pressure_pa'),
      ),
      BatteryCard(batteryPct: d.batteryPct, powerSource: d.powerSource),
    ];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          StatusBanner(
            systemStatus: payload.systemStatus,
            activeAlarmCount: payload.activeAlarms.length,
          ),
          const SizedBox(height: 20),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 250,
              mainAxisExtent: 150,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
            ),
            itemCount: cards.length,
            itemBuilder: (_, i) => cards[i],
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth > 820;
              final trend = _trendPanel(provider);
              final pm = _pmPanel(payload);
              if (wide) {
                return IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(flex: 3, child: trend),
                      const SizedBox(width: 16),
                      Expanded(flex: 2, child: pm),
                    ],
                  ),
                );
              }
              return Column(children: [trend, const SizedBox(height: 16), pm]);
            },
          ),
        ],
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

    return _Panel(
      title: 'LIVE TREND',
      trailing: DropdownButton<String>(
        value: _trendKey,
        underline: const SizedBox.shrink(),
        isDense: true,
        borderRadius: BorderRadius.circular(10),
        style: const TextStyle(
            color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 13),
        items: _trendOptions.entries
            .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value.$1)))
            .toList(),
        onChanged: (v) => setState(() => _trendKey = v ?? _trendKey),
      ),
      child: SizedBox(
        height: 220,
        child: TrendChart(spots: spots, color: meta.$3, unit: meta.$2),
      ),
    );
  }

  Widget _pmPanel(DashboardPayload payload) {
    final d = payload.data;
    return _Panel(
      title: 'PARTICULATE MATTER',
      child: SizedBox(
        height: 220,
        child: PmBreakdown(
          pm1: d.pm1,
          pm25: d.pm25,
          pm10: d.pm10,
          pm1Level: payload.levelFor('pm1_ugm3'),
          pm25Level: payload.levelFor('pm25_ugm3'),
          pm10Level: payload.levelFor('pm10_ugm3'),
        ),
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  final String title;
  final Widget child;
  final Widget? trailing;
  const _Panel({required this.title, required this.child, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: AppColors.textSecondary,
                ),
              ),
              const Spacer(),
              if (trailing != null) trailing!,
            ],
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}
