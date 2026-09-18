import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../../features/auth/auth_service.dart';
import '../../../features/foto/foto_service.dart';

class FotoPage extends StatefulWidget {
  const FotoPage({super.key});

  @override
  State<FotoPage> createState() => _FotoPageState();
}

class _FotoPageState extends State<FotoPage> {
  final _cantiereController = TextEditingController();
  final _descrizioneController = TextEditingController();
  String? _workerId;
  String? _pickedFilePath;
  bool _loading = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    final user = await AuthService.me();
    setState(() => _workerId = user["id"]);
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
    );
    if (result != null && result.files.single.path != null) {
      setState(() => _pickedFilePath = result.files.single.path);
    }
  }

  Future<void> _upload() async {
    if (_workerId == null ||
        _cantiereController.text.isEmpty ||
        _pickedFilePath == null) {
      setState(() => _message = "Seleziona una foto e inserisci l'ID cantiere");
      return;
    }
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      await FotoService.upload(
        cantiereId: _cantiereController.text,
        workerId: _workerId!,
        filePath: _pickedFilePath!,
        descrizione: _descrizioneController.text.isEmpty
            ? null
            : _descrizioneController.text,
      );
      setState(() {
        _message = "Foto caricata con successo";
        _pickedFilePath = null;
      });
    } catch (e) {
      setState(() => _message = "Errore upload: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _cantiereController.dispose();
    _descrizioneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Foto Avanzamento")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _cantiereController,
              decoration: const InputDecoration(
                labelText: "ID Cantiere",
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _descrizioneController,
              decoration: const InputDecoration(
                labelText: "Descrizione (opzionale)",
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: _pickFile,
              icon: const Icon(Icons.photo_library),
              label: const Text("Seleziona foto"),
            ),
            const SizedBox(height: 16),
            if (_pickedFilePath != null)
              SizedBox(
                height: 200,
                child: Image.file(File(_pickedFilePath!), fit: BoxFit.contain),
              ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loading ? null : _upload,
              child: const Text("Carica foto"),
            ),
            const SizedBox(height: 16),
            if (_loading) const Center(child: CircularProgressIndicator()),
            if (_message != null)
              Text(
                _message!,
                style: TextStyle(
                  color: _message!.startsWith("Errore") ? Colors.red : Colors.green,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
