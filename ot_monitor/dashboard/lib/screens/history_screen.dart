import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../providers/dashboard_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/trend_chart.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _rows = [];
  bool _loading = true;
  String? _error;
  double _hours = 1;
  String _metricKey = 'pm25_ugm3';

  static const _metrics = {
    'temperature_c': ('Temperature', '°C', AppColors.temp),
    'relative_humidity_pct': ('Humidity', '%', AppColors.hum),
    'pm25_ugm3': ('PM2.5', 'µg/m³', AppColors.pm25),
    'co2_ppm': ('CO₂', 'ppm', AppColors.co2),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = context.read<DashboardProvider>().api;
      final rows = await api.getHistory(hours: _hours);
      if (mounted) setState(() => _rows = rows);
    } catch (e) {
      if (mounted) setState(() => _error = 'Could not load history: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  double? _num(dynamic v) => v == null ? null : (v as num).toDouble();

  String _fmt(String iso) {
    try {
      return DateFormat('HH:mm:ss').format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final meta = _metrics[_metricKey]!;
    final spots = <FlSpot>[];
    for (var i = 0; i < _rows.length; i++) {
      final v = _num(_rows[i][_metricKey]);
      if (v != null) spots.add(FlSpot(i.toDouble(), v));
    }

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Text('History',
                  style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary)),
              const Spacer(),
              _rangeButton(1, 'Last 1h'),
              const SizedBox(width: 8),
              _rangeButton(6, 'Last 6h'),
              const SizedBox(width: 8),
              _rangeButton(24, 'Last 24h'),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Refresh'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(color: AppColors.accent))
                : _error != null
                    ? Center(
                        child: Text(_error!,
                            style: const TextStyle(color: AppColors.alarm)))
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Container(
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
                                    Text('${meta.$1} trend  (${_rows.length} samples)',
                                        style: const TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w700,
                                            letterSpacing: 1.0,
                                            color: AppColors.textSecondary)),
                                    const Spacer(),
                                    DropdownButton<String>(
                                      value: _metricKey,
                                      underline: const SizedBox.shrink(),
                                      isDense: true,
                                      style: const TextStyle(
                                          color: AppColors.textPrimary,
                                          fontWeight: FontWeight.w600,
                                          fontSize: 13),
                                      items: _metrics.entries
                                          .map((e) => DropdownMenuItem(
                                              value: e.key,
                                              child: Text(e.value.$1)))
                                          .toList(),
                                      onChanged: (v) =>
                                          setState(() => _metricKey = v ?? _metricKey),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 14),
                                SizedBox(
                                  height: 200,
                                  child: TrendChart(
                                      spots: spots,
                                      color: meta.$3,
                                      unit: meta.$2),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 16),
                          Expanded(child: _table()),
                        ],
                      ),
          ),
        ],
      ),
    );
  }

  Widget _rangeButton(double hours, String label) {
    final selected = _hours == hours;
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) {
        setState(() => _hours = hours);
        _load();
      },
      selectedColor: AppColors.accent.withValues(alpha: 0.15),
      labelStyle: TextStyle(
        color: selected ? AppColors.accentDark : AppColors.textSecondary,
        fontWeight: FontWeight.w600,
        fontSize: 12,
      ),
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(
            color: selected ? AppColors.accent : AppColors.border),
      ),
    );
  }

  Widget _table() {
    if (_rows.isEmpty) {
      return const Center(
        child: Text('No data recorded for this range yet.',
            style: TextStyle(color: AppColors.textSecondary)),
      );
    }
    // Show most recent first, cap to keep the table responsive.
    final rows = _rows.reversed.take(200).toList();
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: SingleChildScrollView(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              headingRowColor:
                  WidgetStateProperty.all(AppColors.surfaceAlt),
              headingTextStyle: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  color: AppColors.textSecondary),
              dataTextStyle: const TextStyle(
                  fontSize: 12, color: AppColors.textPrimary),
              columns: const [
                DataColumn(label: Text('Time')),
                DataColumn(label: Text('Temp °C')),
                DataColumn(label: Text('Hum %')),
                DataColumn(label: Text('PM2.5')),
                DataColumn(label: Text('PM10')),
                DataColumn(label: Text('CO₂')),
                DataColumn(label: Text('Status')),
              ],
              rows: rows.map((r) {
                String s(dynamic v, [int dp = 1]) =>
                    v == null ? '—' : (v as num).toStringAsFixed(dp);
                return DataRow(cells: [
                  DataCell(Text(_fmt('${r['timestamp_iso']}'))),
                  DataCell(Text(s(r['temperature_c']))),
                  DataCell(Text(s(r['relative_humidity_pct']))),
                  DataCell(Text(s(r['pm25_ugm3']))),
                  DataCell(Text(s(r['pm10_ugm3']))),
                  DataCell(Text(s(r['co2_ppm'], 0))),
                  DataCell(Text('${r['system_status'] ?? '—'}')),
                ]);
              }).toList(),
            ),
          ),
        ),
      ),
    );
  }
}
