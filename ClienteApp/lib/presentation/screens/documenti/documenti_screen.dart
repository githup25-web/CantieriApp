import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class DocumentiScreen extends StatefulWidget {
  const DocumentiScreen({super.key, required this.idCantiere});

  final int idCantiere;

  @override
  State<DocumentiScreen> createState() => _DocumentiScreenState();
}

class _DocumentiScreenState extends State<DocumentiScreen> {
  bool _isLoading = false;
  String? _error;

  List<DocumentoDto> _documenti = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _documenti = const [];
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('jwt_token');

      if (token == null || token.trim().isEmpty) {
        setState(() {
          _error = 'Sessione non valida. Effettua il login.';
        });
        return;
      }

      const baseUrl = 'http://localhost:8000';
      final uri =
          Uri.parse('$baseUrl/cliente/area/cantiere/${widget.idCantiere}/documenti');

      final res = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (res.statusCode < 200 || res.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare i documenti.';
        });
        return;
      }

      final decoded = jsonDecode(res.body);
      final list = _extractList(decoded);

      setState(() {
        _documenti = list.map((e) => DocumentoDto.fromJson(e)).toList();
      });
    } catch (_) {
      setState(() {
        _error = 'Errore di rete. Riprova.';
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  List<dynamic> _extractList(dynamic decoded) {
    if (decoded == null) return const [];
    if (decoded is List) return decoded;
    if (decoded is Map<String, dynamic>) {
      final v = decoded['documenti'] ?? decoded['items'] ?? decoded['data'] ?? decoded['list'];
      if (v is List) return v;
    }
    return const [];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Documenti')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ),
                )
              : _documenti.isEmpty
                  ? const Center(child: Text('Nessun documento disponibile.'))
                  : ListView.separated(
                      padding: const EdgeInsets.all(8),
                      itemCount: _documenti.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, i) {
                        final d = _documenti[i];
                        return ListTile(
                          leading: Icon(_iconForName(d.nome)),
                          title: Text(
                            d.nome,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => DocumentoFileScreen(
                                  idCantiere: widget.idCantiere,
                                  documento: d,
                                ),
                              ),
                            );
                          },
                        );
                      },
                    ),
    );
  }

  IconData _iconForName(String nome) {
    final n = nome.toLowerCase();
    if (n.endsWith('.pdf')) return Icons.picture_as_pdf;
    if (n.endsWith('.doc') || n.endsWith('.docx')) return Icons.description;
    if (n.endsWith('.xls') || n.endsWith('.xlsx')) return Icons.table_chart;
    if (n.endsWith('.jpg') || n.endsWith('.jpeg') || n.endsWith('.png')) return Icons.image;
    return Icons.insert_drive_file;
  }
}

class DocumentoFileScreen extends StatefulWidget {
  const DocumentoFileScreen({
    super.key,
    required this.idCantiere,
    required this.documento,
  });

  final int idCantiere;
  final DocumentoDto documento;

  @override
  State<DocumentoFileScreen> createState() => _DocumentoFileScreenState();
}

class _DocumentoFileScreenState extends State<DocumentoFileScreen> {
  bool _isDownloading = false;

  @override
  Widget build(BuildContext context) {
    final doc = widget.documento;
    final url = doc.url ?? '';

    return Scaffold(
      appBar: AppBar(title: Text(doc.nome)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'URL:',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            SelectableText(
              url.isEmpty ? 'Nessun URL disponibile.' : url,
              maxLines: 5,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            if (url.isEmpty)
              const Text('Impossibile scaricare: URL mancante.')
            else
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _isDownloading
                      ? null
                      : () async {
                          setState(() => _isDownloading = true);
                          try {
                            final prefs = await SharedPreferences.getInstance();
                            final token = prefs.getString('jwt_token') ?? '';
                            final res = await http.get(
                              Uri.parse(url),
                              headers: token.trim().isEmpty
                                  ? {'Content-Type': 'application/json'}
                                  : {
                                      'Content-Type': 'application/json',
                                      'Authorization': 'Bearer $token',
                                    },
                            );
                            if (res.statusCode < 200 || res.statusCode >= 300) {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Download fallito.')),
                                );
                              }
                              return;
                            }
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Download completato.')),
                              );
                            }
                          } catch (_) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Errore di rete. Riprova.')),
                              );
                            }
                          } finally {
                            if (mounted) setState(() => _isDownloading = false);
                          }
                        },
                  icon: _isDownloading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.download),
                  label: Text(_isDownloading ? 'Scarico...' : 'Scarica'),
                ),
              ),
            const SizedBox(height: 16),
            Text(
              'Dopo il download la schermata non mostra un viewer. Usa la tua gestione file di sistema se supportata dalla piattaforma.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class DocumentoDto {
  DocumentoDto({required this.nome, required this.url});

  final String nome;
  final String? url;

  factory DocumentoDto.fromJson(Map<String, dynamic> json) {
    String parseString(dynamic v) => v == null ? '' : v.toString();
    final nome = parseString(json['nome'] ?? json['filename'] ?? json['file_name'] ?? json['titolo'] ?? json['name']);
    final url = json['url'] ?? json['link'] ?? json['path'] ?? json['file_url'] ?? json['file'];
    final urlStr = url == null ? null : parseString(url);
    return DocumentoDto(nome: nome.isEmpty ? 'Documento' : nome, url: urlStr);
  }
}
