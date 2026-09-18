import 'package:flutter/material.dart';

import '../../../features/presenze/presenze_service.dart';
import '../foto/foto_page.dart';
import '../tasks/tasks_page.dart';

class CantierePage extends StatefulWidget {
  const CantierePage({super.key});

  @override
  State<CantierePage> createState() => _CantierePageState();
}

class _CantierePageState extends State<CantierePage> {
  final _cantiereController = TextEditingController();
  String? _cantiereId;

  @override
  void dispose() {
    _cantiereController.dispose();
    super.dispose();
  }

  void _apriCantiere() {
    if (_cantiereController.text.isEmpty) return;
    setState(() => _cantiereId = _cantiereController.text);
  }

  @override
  Widget build(BuildContext context) {
    final cantiereId = _cantiereId;

    return Scaffold(
      appBar: AppBar(title: const Text("Gestione Cantiere")),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _cantiereController,
                    decoration: const InputDecoration(
                      labelText: "ID Cantiere",
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _apriCantiere(),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _apriCantiere,
                  child: const Text("Apri"),
                ),
              ],
            ),
          ),
          Expanded(
            child: cantiereId == null
                ? const Center(
                    child: Text("Inserisci l'ID di un cantiere per iniziare"),
                  )
                : DefaultTabController(
                    length: 3,
                    child: Column(
                      children: [
                        const TabBar(
                          tabs: [
                            Tab(text: "Task", icon: Icon(Icons.checklist)),
                            Tab(text: "Presenze", icon: Icon(Icons.people)),
                            Tab(text: "Foto", icon: Icon(Icons.photo_library)),
                          ],
                        ),
                        Expanded(
                          child: TabBarView(
                            children: [
                              TasksPage(cantiereId: cantiereId),
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

class _PresenzeTab extends StatefulWidget {
  final String cantiereId;

  const _PresenzeTab({required this.cantiereId});

  @override
  State<_PresenzeTab> createState() => _PresenzeTabState();
}

class _PresenzeTabState extends State<_PresenzeTab> {
  List<dynamic> _presenze = [];
  bool _loading = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final presenze = await PresenzeService.listByCantiere(widget.cantiereId);
      setState(() => _presenze = presenze);
    } catch (e) {
      setState(() => _message = "Errore caricamento presenze: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  "Presenze del cantiere ${widget.cantiereId}",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              IconButton(
                onPressed: _loading ? null : _load,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_loading) const LinearProgressIndicator(),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(_message!, style: const TextStyle(color: Colors.red)),
            ),
          Expanded(
            child: _presenze.isEmpty
                ? const Center(child: Text("Nessuna presenza registrata"))
                : ListView.separated(
                    itemCount: _presenze.length,
                    separatorBuilder: (_, __) => const Divider(),
                    itemBuilder: (context, index) {
                      final presenza = _presenze[index] as Map<String, dynamic>;
                      final inCantiere = presenza["checkout"] == null;
                      return ListTile(
                        leading: Icon(
                          inCantiere ? Icons.login : Icons.logout,
                          color: inCantiere ? Colors.green : Colors.grey,
                        ),
                        title: Text("Worker: ${presenza["worker_id"]}"),
                        subtitle: Text(
                          "Check-in: ${presenza["checkin"]}\n"
                          "Check-out: ${presenza["checkout"] ?? "-"}",
                        ),
                        isThreeLine: true,
                        trailing: Chip(
                          label: Text(inCantiere ? "In cantiere" : "Fuori"),
                          backgroundColor:
                              inCantiere ? Colors.green.shade100 : Colors.grey.shade300,
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
