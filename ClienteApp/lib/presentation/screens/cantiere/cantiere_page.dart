import 'package:flutter/material.dart';

import '../../../features/presenze/presenze_service.dart';
import 'avanzamento_page.dart';
import 'foto_page.dart';

class CantierePage extends StatefulWidget {
  const CantierePage({super.key});

  @override
  State<CantierePage> createState() => _CantierePageState();
}

class _CantierePageState extends State<CantierePage> {
  final _controller = TextEditingController();
  String? _cantiereId;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _apri() {
    final id = _controller.text.trim();
    if (id.isEmpty) return;
    setState(() => _cantiereId = id);
  }

  @override
  Widget build(BuildContext context) {
    final cantiereId = _cantiereId;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Avanzamento Cantiere'),
      ),
      body: Column(
        children: [
          // ── Input cantiere_id ──────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _apri(),
                    decoration: const InputDecoration(
                      labelText: 'ID Cantiere',
                      hintText: 'Inserisci l\'ID del cantiere',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.construction),
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _apri,
                  child: const Text('Apri'),
                ),
              ],
            ),
          ),

          // ── Contenuto principale ───────────────────────────────────────────
          Expanded(
            child: cantiereId == null
                ? const Center(
                    child: Text(
                      'Inserisci l\'ID di un cantiere per visualizzare\nl\'avanzamento dei lavori.',
                      textAlign: TextAlign.center,
                    ),
                  )
                : DefaultTabController(
                    length: 3,
                    child: Column(
                      children: [
                        const SizedBox(height: 12),
                        const TabBar(
                          tabs: [
                            Tab(
                              text: 'Avanzamento',
                              icon: Icon(Icons.bar_chart_rounded),
                            ),
                            Tab(
                              text: 'Presenze',
                              icon: Icon(Icons.people_alt_rounded),
                            ),
                            Tab(
                              text: 'Foto',
                              icon: Icon(Icons.photo_library_rounded),
                            ),
                          ],
                          labelStyle: TextStyle(
                            fontWeight: FontWeight.w700,
                          ),
                          indicatorSize: TabBarIndicatorSize.tab,
                        ),
                        Expanded(
                          child: TabBarView(
                            children: [
                              AvanzamentoPage(cantiereId: cantiereId),
                              _PresenzeTab(cantiereId: cantiereId),
                              FotoPage(cantiereId: cantiereId),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

// ── Tab presenze inline ───────────────────────────────────────────────────────

class _PresenzeTab extends StatefulWidget {
  final String cantiereId;

  const _PresenzeTab({required this.cantiereId});

  @override
  State<_PresenzeTab> createState() => _PresenzeTabState();
}

class _PresenzeTabState extends State<_PresenzeTab> {
  List<dynamic> _presenze = [];
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
      final presenze =
          await PresenzeService.listByCantiere(widget.cantiereId);
      setState(() => _presenze = presenze);
    } catch (e) {
      setState(() => _error = 'Errore caricamento presenze: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  String _formatDatetime(String? raw) {
    if (raw == null || raw.isEmpty) return '—';
    final parts = raw.split('T');
    final date = parts[0];
    final time = parts.length > 1 ? parts[1].split('.').first : '';
    return time.isEmpty ? date : '$date $time';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!,
                  style: TextStyle(color: scheme.error),
                  textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Riprova'),
              ),
            ],
          ),
        ),
      );
    }

    if (_presenze.isEmpty) {
      return RefreshIndicator(
        onRefresh: _load,
        child: const CustomScrollView(
          slivers: [
            SliverFillRemaining(
              child: Center(child: Text('Nessuna presenza registrata')),
            ),
          ],
        ),
      );
    }

    // Conta lavoratori attualmente in cantiere (checkout == null)
    final inCantiere = _presenze
        .whereType<Map<String, dynamic>>()
        .where((p) => p['checkout'] == null)
        .length;

    return RefreshIndicator(
      onRefresh: _load,
      child: CustomScrollView(
        slivers: [
          // ── Banner riepilogo ───────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Card(
                elevation: 0,
                color: scheme.surfaceContainerHighest,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 20, vertical: 14),
                  child: Row(
                    children: [
                      Icon(Icons.people_alt_rounded,
                          size: 36, color: scheme.primary),
                      const SizedBox(width: 16),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'In cantiere ora',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          Text(
                            '$inCantiere lavorator${inCantiere == 1 ? 'e' : 'i'}',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    color: inCantiere > 0
                                        ? const Color(0xFF2E7D32)
                                        : scheme.outline),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ── Lista presenze ────────────────────────────────────────────────
          SliverPadding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16),
            sliver: SliverList.separated(
              itemCount: _presenze.length,
              separatorBuilder: (_, __) =>
                  const Divider(height: 1),
              itemBuilder: (context, index) {
                final p =
                    _presenze[index] as Map<String, dynamic>;
                final inCantiere = p['checkout'] == null;
                final checkinStr =
                    _formatDatetime(p['checkin'] as String?);
                final checkoutStr =
                    _formatDatetime(p['checkout'] as String?);

                return ListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 4),
                  leading: CircleAvatar(
                    backgroundColor: inCantiere
                        ? const Color(0xFFE8F5E9)
                        : scheme.surfaceContainerHighest,
                    child: Icon(
                      inCantiere
                          ? Icons.login_rounded
                          : Icons.logout_rounded,
                      color: inCantiere
                          ? const Color(0xFF2E7D32)
                          : scheme.outline,
                    ),
                  ),
                  title: Text(
                    p['worker_id'] as String? ?? '—',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.login_rounded,
                              size: 14),
                          const SizedBox(width: 4),
                          Text(
                            'Check-in: $checkinStr',
                            style:
                                Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          const Icon(Icons.logout_rounded,
                              size: 14),
                          const SizedBox(width: 4),
                          Text(
                            'Check-out: $checkoutStr',
                            style:
                                Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ],
                  ),
                  isThreeLine: true,
                  trailing: Chip(
                    label: Text(
                      inCantiere ? 'In cantiere' : 'Uscito',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: inCantiere
                            ? const Color(0xFF2E7D32)
                            : scheme.outline,
                      ),
                    ),
                    backgroundColor: inCantiere
                        ? const Color(0xFFE8F5E9)
                        : scheme.surfaceContainerHighest,
                    side: BorderSide.none,
                    visualDensity: VisualDensity.compact,
                  ),
                );
              },
            ),
          ),
          const SliverPadding(padding: EdgeInsets.only(bottom: 16)),
        ],
      ),
    );
  }
}
