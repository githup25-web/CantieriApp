import 'package:flutter/material.dart';

import '../../../features/cantiere/cantiere_service.dart';
import '../../../features/tasks/task_service.dart';

const _statoLabels = {
  'completato': 'Completato',
  'in_corso': 'In corso',
  'in_attesa': 'In attesa',
};

const _statoColors = {
  'completato': Color(0xFF2E7D32),
  'in_corso': Color(0xFF1565C0),
  'in_attesa': Color(0xFF757575),
};

class AvanzamentoPage extends StatefulWidget {
  final String cantiereId;

  const AvanzamentoPage({super.key, required this.cantiereId});

  @override
  State<AvanzamentoPage> createState() => _AvanzamentoPageState();
}

class _AvanzamentoPageState extends State<AvanzamentoPage> {
  List<dynamic> _tasks = [];
  AvanzamentoResult? _avanzamento;
  bool _loading = false;
  String? _error;

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
      final tasks = await TaskService.listByCantiere(widget.cantiereId);
      final avanzamento = CantiereService.calcolaAvanzamento(tasks);
      setState(() {
        _tasks = tasks;
        _avanzamento = avanzamento;
      });
    } catch (e) {
      setState(() => _error = 'Errore caricamento task: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final avanzamento = _avanzamento;

    return RefreshIndicator(
      onRefresh: _load,
      child: CustomScrollView(
        slivers: [
          // ── Pannello avanzamento ─────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Card(
                elevation: 0,
                color: scheme.surfaceContainerHighest,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: _loading
                      ? const Center(child: CircularProgressIndicator())
                      : _error != null
                          ? Text(
                              _error!,
                              style: TextStyle(color: scheme.error),
                            )
                          : avanzamento == null
                              ? const Text('Nessun dato')
                              : Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            'Avanzamento lavori',
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium
                                                ?.copyWith(
                                                    fontWeight: FontWeight.w700),
                                          ),
                                        ),
                                        _PercentualeCircle(
                                          value: avanzamento.percentuale,
                                          label:
                                              '${avanzamento.percentualeInt}%',
                                          color: scheme.primary,
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 14),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: LinearProgressIndicator(
                                        value: avanzamento.percentuale,
                                        minHeight: 12,
                                        backgroundColor:
                                           scheme.surfaceContainerHighest,
                                        valueColor:
                                            AlwaysStoppedAnimation<Color>(
                                                scheme.primary),
                                      ),
                                    ),
                                    const SizedBox(height: 16),
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceAround,
                                      children: [
                                        _StatBadge(
                                          label: 'Totale',
                                          value: avanzamento.totale,
                                          color: scheme.onSurface,
                                        ),
                                        _StatBadge(
                                          label: 'Completati',
                                          value: avanzamento.completati,
                                          color: const Color(0xFF2E7D32),
                                        ),
                                        _StatBadge(
                                          label: 'In corso',
                                          value: avanzamento.inCorso,
                                          color: const Color(0xFF1565C0),
                                        ),
                                        _StatBadge(
                                          label: 'In attesa',
                                          value: avanzamento.inAttesa,
                                          color: const Color(0xFF757575),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                ),
              ),
            ),
          ),

          // ── Lista task ────────────────────────────────────────────────────────
          if (!_loading && _error == null)
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              sliver: SliverList.separated(
                itemCount: _tasks.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final task = _tasks[index] as Map<String, dynamic>;
                  final stato = task['stato'] as String? ?? 'in_attesa';
                  final statoColor =
                      _statoColors[stato] ?? const Color(0xFF757575);
                  final scadenza = task['data_scadenza'] as String?;

                  return ListTile(
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                    leading: Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        color: statoColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                    title: Text(
                      task['titolo'] as String? ?? '',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(task['descrizione'] as String? ?? ''),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Chip(
                              label: Text(
                                _statoLabels[stato] ?? stato,
                                style: TextStyle(
                                    color: statoColor,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700),
                              ),
                              side: BorderSide(
                                  color: statoColor.withAlpha(77)),
                              backgroundColor:
                                  statoColor.withAlpha(26),
                              visualDensity: VisualDensity.compact,
                            ),
                            if (scadenza != null) ...[
                              const SizedBox(width: 6),
                              Text(
                                'Scad: ${scadenza.split('T').first}',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: scheme.outline),
                              ),
                            ],
                          ],
                        ),
                        Text(
                          'Assegnato: ${task["assegnato_a"] ?? "—"}',
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: scheme.outline),
                        ),
                      ],
                    ),
                    isThreeLine: true,
                  );
                },
              ),
            ),

          if (!_loading && _tasks.isEmpty && _error == null)
            const SliverFillRemaining(
              child: Center(child: Text('Nessun task per questo cantiere')),
            ),
        ],
      ),
    );
  }
}

// ── Widget ausiliari ──────────────────────────────────────────────────────────

class _PercentualeCircle extends StatelessWidget {
  const _PercentualeCircle({
    required this.value,
    required this.label,
    required this.color,
  });

  final double value;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 64,
      height: 64,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            value: value,
            strokeWidth: 7,
            backgroundColor: color.withAlpha(51),
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatBadge extends StatelessWidget {
  const _StatBadge({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          '$value',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w800,
            color: color,
          ),
        ),
        Text(
          label,
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: color.withAlpha(204)),
        ),
      ],
    );
  }
}
