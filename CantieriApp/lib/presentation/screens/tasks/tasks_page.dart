import 'package:flutter/material.dart';

import '../../../features/tasks/task_service.dart';

const _statoOptions = ["in_attesa", "in_corso", "completato"];

class TasksPage extends StatefulWidget {
  final String cantiereId;

  const TasksPage({super.key, required this.cantiereId});

  @override
  State<TasksPage> createState() => _TasksPageState();
}

class _TasksPageState extends State<TasksPage> {
  final _titoloController = TextEditingController();
  final _descrizioneController = TextEditingController();
  final _assegnatoAController = TextEditingController();
  String _nuovoStato = _statoOptions.first;

  List<dynamic> _tasks = [];
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
      final tasks = await TaskService.listByCantiere(widget.cantiereId);
      setState(() => _tasks = tasks);
    } catch (e) {
      setState(() => _message = "Errore caricamento task: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _createTask() async {
    if (_titoloController.text.isEmpty ||
        _descrizioneController.text.isEmpty ||
        _assegnatoAController.text.isEmpty) {
      setState(() => _message = "Compila titolo, descrizione e assegnatario");
      return;
    }
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      await TaskService.create(
        cantiereId: widget.cantiereId,
        titolo: _titoloController.text,
        descrizione: _descrizioneController.text,
        assegnatoA: _assegnatoAController.text,
        stato: _nuovoStato,
      );
      _titoloController.clear();
      _descrizioneController.clear();
      _assegnatoAController.clear();
      setState(() => _message = "Task creato con successo");
      await _load();
    } catch (e) {
      setState(() => _message = "Errore creazione task: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _updateStato(String taskId, String nuovoStato) async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      await TaskService.update(taskId, stato: nuovoStato);
      await _load();
    } catch (e) {
      setState(() => _message = "Errore aggiornamento stato: $e");
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _titoloController.dispose();
    _descrizioneController.dispose();
    _assegnatoAController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            "Task del cantiere ${widget.cantiereId}",
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          ExpansionTile(
            title: const Text("Crea nuovo task"),
            initiallyExpanded: false,
            children: [
              TextField(
                controller: _titoloController,
                decoration: const InputDecoration(
                  labelText: "Titolo",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _descrizioneController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: "Descrizione",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _assegnatoAController,
                decoration: const InputDecoration(
                  labelText: "Assegnato a (worker id)",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _nuovoStato,
                decoration: const InputDecoration(
                  labelText: "Stato iniziale",
                  border: OutlineInputBorder(),
                ),
                items: _statoOptions
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (value) {
                  if (value != null) setState(() => _nuovoStato = value);
                },
              ),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: _loading ? null : _createTask,
                icon: const Icon(Icons.add_task),
                label: const Text("Crea task"),
              ),
              const SizedBox(height: 8),
            ],
          ),
          const SizedBox(height: 12),
          if (_loading) const LinearProgressIndicator(),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                _message!,
                style: TextStyle(
                  color: _message!.startsWith("Errore") ? Colors.red : Colors.green,
                ),
              ),
            ),
          Expanded(
            child: _tasks.isEmpty
                ? const Center(child: Text("Nessun task per questo cantiere"))
                : ListView.separated(
                    itemCount: _tasks.length,
                    separatorBuilder: (_, __) => const Divider(),
                    itemBuilder: (context, index) {
                      final task = _tasks[index] as Map<String, dynamic>;
                      final stato = task["stato"] as String? ?? "in_attesa";
                      return ListTile(
                        title: Text(task["titolo"] ?? ""),
                        subtitle: Text(
                          "${task["descrizione"] ?? ""}\nAssegnato a: ${task["assegnato_a"] ?? ""}",
                        ),
                        isThreeLine: true,
                        trailing: DropdownButton<String>(
                          value: _statoOptions.contains(stato) ? stato : _statoOptions.first,
                          items: _statoOptions
                              .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                              .toList(),
                          onChanged: _loading
                              ? null
                              : (value) {
                                  if (value != null) {
                                    _updateStato(task["id"] as String, value);
                                  }
                                },
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
