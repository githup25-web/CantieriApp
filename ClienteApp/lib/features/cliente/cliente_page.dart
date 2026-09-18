import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../cantiere/cantiere_service.dart';
import 'cliente_service.dart';

class ClientePage extends StatefulWidget {
  const ClientePage({super.key});

  @override
  State<ClientePage> createState() => _ClientePageState();
}

class _ClientePageState extends State<ClientePage> {
  final _codeController = TextEditingController();
  final _storage = const FlutterSecureStorage();

  bool _isLoading = false;
  String? _error;
  List<dynamic> _cantieri = const [];

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      setState(() => _error = 'Inserisci il codice cliente');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final result = await ClienteService.login(code);
      final token = result['token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('Token mancante');
      }

      await _storage.write(key: 'access_token', value: token);
      await _loadCantieri();
    } catch (_) {
      setState(() => _error = 'Codice non valido. Contatta l\'azienda.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadCantieri() async {
    try {
      final cantieri = await ClienteService.getCantieri();
      setState(() => _cantieri = cantieri);
    } catch (_) {
      setState(() => _error = 'Errore caricamento cantieri');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Area Cliente')),
      body: _cantieri.isEmpty && !_isLoading
          ? _buildLoginView()
          : _buildCantieriView(),
    );
  }

  Widget _buildLoginView() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.verified_user_outlined,
                  size: 64, color: Colors.blueGrey),
              const SizedBox(height: 16),
              Text(
                'Accedi con il tuo codice',
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              TextField(
                controller: _codeController,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _login(),
                decoration: const InputDecoration(
                  labelText: 'Codice cliente',
                  hintText: 'Es: CANT-123456',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.code),
                ),
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _isLoading ? null : _login,
                child: _isLoading
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Accedi'),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCantieriView() {
    if (_cantieri.isEmpty) {
      return const Center(child: Text('Nessun cantiere assegnato'));
    }

    return RefreshIndicator(
      onRefresh: _loadCantieri,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _cantieri.length,
        itemBuilder: (context, index) {
          final cantiere = _cantieri[index] as Map<String, dynamic>;
          final id = cantiere['id'] as String? ?? '';
          final title = cantiere['titolo'] as String? ??
              cantiere['nome_cantiere'] as String? ??
              'Cantiere';
          final stato = cantiere['stato'] as String? ??
              cantiere['status'] as String? ??
              '';
          final progress = (cantiere['percentuale_avanzamento'] as num?)?.toInt() ??
              (cantiere['percentuale'] as num?)?.toInt() ??
              0;

          return Card(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: Theme.of(context).dividerColor),
            ),
            child: ListTile(
              leading: const CircleAvatar(child: Icon(Icons.construction)),
              title: Text(title,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(stato),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(
                    value: progress / 100,
                    minHeight: 6,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ],
              ),
              isThreeLine: true,
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => _CantiereDettaglioPage(cantiereId: id),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _CantiereDettaglioPage extends StatefulWidget {
  final String cantiereId;

  const _CantiereDettaglioPage({required this.cantiereId});

  @override
  State<_CantiereDettaglioPage> createState() => _CantiereDettaglioPageState();
}

class _CantiereDettaglioPageState extends State<_CantiereDettaglioPage> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Dettaglio Cantiere'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Avanzamento', icon: Icon(Icons.bar_chart)),
              Tab(text: 'Presenze', icon: Icon(Icons.people)),
              Tab(text: 'Foto', icon: Icon(Icons.photo)),
              Tab(text: 'Notifiche', icon: Icon(Icons.notifications)),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _AvanzamentoTab(cantiereId: widget.cantiereId),
            _PresenzeTab(cantiereId: widget.cantiereId),
            _FotoTab(cantiereId: widget.cantiereId),
            _NotificheTab(cantiereId: widget.cantiereId),
          ],
        ),
      ),
    );
  }
}

class _AvanzamentoTab extends StatefulWidget {
  final String cantiereId;

  const _AvanzamentoTab({required this.cantiereId});

  @override
  State<_AvanzamentoTab> createState() => _AvanzamentoTabState();
}

class _AvanzamentoTabState extends State<_AvanzamentoTab> {
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
      final data = await ClienteService.getAvanzamento();
      final tasks = (data['tasks'] as List<dynamic>?) ?? const [];

      // Converti i task dal formato backend (title/status) al formato atteso
      final converted = tasks.map((raw) {
        final t = raw as Map<String, dynamic>;
        return {
          'titolo': t['title'] ?? '',
          'descrizione': t['description'] ?? '',
          'stato': t['status'] ?? '',
          'progress': t['progress'] ?? 0,
        };
      }).toList();

      final avanzamento = CantiereService.calcolaAvanzamento(converted);
      setState(() {
        _tasks = converted;
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

    if (avanzamento == null) {
      return const Center(child: Text('Nessun dato'));
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            color: scheme.surfaceContainerHighest,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Avanzamento lavori',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 14),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: LinearProgressIndicator(
                      value: avanzamento.percentuale,
                      minHeight: 12,
                      backgroundColor: scheme.surfaceContainerHighest,
                      valueColor: AlwaysStoppedAnimation<Color>(scheme.primary),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    '${avanzamento.percentualeInt}% completato',
                    style: Theme.of(context)
                        .textTheme
                        .titleLarge
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _StatBadge(label: 'Totale', value: avanzamento.totale),
                      _StatBadge(
                          label: 'Completati', value: avanzamento.completati),
                      _StatBadge(label: 'In corso', value: avanzamento.inCorso),
                      _StatBadge(label: 'In attesa', value: avanzamento.inAttesa),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (_tasks.isEmpty)
            const Center(child: Text('Nessun task per questo cantiere'))
          else
            ..._tasks.map((raw) {
              final task = raw as Map<String, dynamic>;
              return ListTile(
                leading: const Icon(Icons.check_circle_outline),
                title: Text(task['titolo'] as String? ?? ''),
                subtitle: Text(task['descrizione'] as String? ?? ''),
                trailing: Chip(label: Text(task['stato'] as String? ?? '')),
              );
            }),
        ],
      ),
    );
  }
}

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
      final presenze = await ClienteService.getPresenze();
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
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(_error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
      );
    }

    if (_presenze.isEmpty) {
      return const Center(child: Text('Nessuna presenza registrata'));
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        itemCount: _presenze.length,
        itemBuilder: (context, index) {
          final p = _presenze[index] as Map<String, dynamic>;
          final type = p['type'] as String? ?? '';
          final isEntrata = type == 'entrata';
          final timestamp = _formatDatetime(p['timestamp'] as String?);

          return ListTile(
            leading: CircleAvatar(
              backgroundColor: isEntrata ? Colors.green.shade100 : null,
              child: Icon(
                isEntrata ? Icons.login : Icons.logout,
                color: isEntrata ? Colors.green.shade800 : null,
              ),
            ),
            title: Text(p['user_id'] as String? ?? '—'),
            subtitle: Text('$type — $timestamp'),
            isThreeLine: false,
          );
        },
      ),
    );
  }
}

class _FotoTab extends StatefulWidget {
  final String cantiereId;

  const _FotoTab({required this.cantiereId});

  @override
  State<_FotoTab> createState() => _FotoTabState();
}

class _FotoTabState extends State<_FotoTab> {
  List<dynamic> _foto = [];
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
      final foto = await ClienteService.getFoto();
      setState(() => _foto = foto);
    } catch (e) {
      setState(() => _error = 'Errore caricamento foto: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(_error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
      );
    }

    if (_foto.isEmpty) {
      return const Center(child: Text('Nessuna foto caricata'));
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
        ),
        itemCount: _foto.length,
        itemBuilder: (context, index) {
          final foto = _foto[index] as Map<String, dynamic>;
          final url = foto['url'] as String? ?? '';
          return Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: url.startsWith('http')
                      ? Image.network(url, fit: BoxFit.cover, width: double.infinity)
                      : Image.network(
                          'http://127.0.0.1:8000$url',
                          fit: BoxFit.cover,
                          width: double.infinity,
                          errorBuilder: (_, __, ___) => const Center(
                              child: Icon(Icons.broken_image, size: 40)),
                        ),
                ),
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text(
                    foto['description'] as String? ?? '',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _NotificheTab extends StatefulWidget {
  final String cantiereId;

  const _NotificheTab({required this.cantiereId});

  @override
  State<_NotificheTab> createState() => _NotificheTabState();
}

class _NotificheTabState extends State<_NotificheTab> {
  List<dynamic> _notifiche = [];
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
      final notifiche = await ClienteService.getNotifiche();
      setState(() => _notifiche = notifiche);
    } catch (e) {
      setState(() => _error = 'Errore caricamento notifiche: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(_error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
      );
    }

    if (_notifiche.isEmpty) {
      return const Center(child: Text('Nessuna notifica'));
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        itemCount: _notifiche.length,
        itemBuilder: (context, index) {
          final n = _notifiche[index] as Map<String, dynamic>;
          final type = n['type'] as String? ?? '';
          final timeAgo = n['time_ago'] as String? ?? '';
          final isRead = n['is_read'] as bool? ?? false;

          return ListTile(
            leading: CircleAvatar(
              child: Icon(isRead ? Icons.notifications_none : Icons.notifications),
            ),
            title: Text(type),
            subtitle: Text(timeAgo),
            trailing: isRead ? null : const Icon(Icons.circle, size: 10, color: Colors.blue),
          );
        },
      ),
    );
  }
}

class _StatBadge extends StatelessWidget {
  const _StatBadge({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          '$value',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
        ),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
