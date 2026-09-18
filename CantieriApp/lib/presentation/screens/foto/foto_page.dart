import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../features/foto/foto_service.dart';

class FotoPage extends StatefulWidget {
  final String cantiereId;

  const FotoPage({super.key, required this.cantiereId});

  @override
  State<FotoPage> createState() => _FotoPageState();
}

class _FotoPageState extends State<FotoPage> {
  List<dynamic> _foto = [];
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
      final foto = await FotoService.listByCantiere(widget.cantiereId);
      setState(() => _foto = foto);
    } catch (e) {
      setState(() => _message = "Errore caricamento foto: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  String _fullUrl(String url) {
    if (url.startsWith("http")) return url;
    return "${ApiClient.dio.options.baseUrl}$url";
  }

  void _showDetail(Map<String, dynamic> foto) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Dettaglio foto"),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Image.network(
                _fullUrl(foto["url"] as String),
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) =>
                    const Icon(Icons.broken_image, size: 64),
              ),
              const SizedBox(height: 12),
              Text("Autore (worker id): ${foto["worker_id"]}"),
              const SizedBox(height: 4),
              Text("Timestamp: ${foto["timestamp"]}"),
              if (foto["descrizione"] != null) ...[
                const SizedBox(height: 4),
                Text("Descrizione: ${foto["descrizione"]}"),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Chiudi"),
          ),
        ],
      ),
    );
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
                  "Foto avanzamento del cantiere ${widget.cantiereId}",
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
            child: _foto.isEmpty
                ? const Center(child: Text("Nessuna foto per questo cantiere"))
                : GridView.builder(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 8,
                    ),
                    itemCount: _foto.length,
                    itemBuilder: (context, index) {
                      final foto = _foto[index] as Map<String, dynamic>;
                      return GestureDetector(
                        onTap: () => _showDetail(foto),
                        child: GridTile(
                          footer: GridTileBar(
                            backgroundColor: Colors.black45,
                            title: Text(
                              (foto["timestamp"] as String? ?? "").split("T").first,
                              style: const TextStyle(fontSize: 11),
                            ),
                          ),
                          child: Image.network(
                            _fullUrl(foto["url"] as String),
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) =>
                                const Icon(Icons.broken_image),
                          ),
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
