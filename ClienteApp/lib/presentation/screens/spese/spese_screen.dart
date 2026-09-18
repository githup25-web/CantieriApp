import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class SpeseScreen extends StatefulWidget {
  const SpeseScreen({super.key, required this.idCantiere});

  final int idCantiere;

  @override
  State<SpeseScreen> createState() => _SpeseScreenState();
}

class _SpeseScreenState extends State<SpeseScreen> {
  bool _isLoading = false;
  String? _error;

  List<SpesaDto> _spese = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _spese = const [];
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
      final uri = Uri.parse('$baseUrl/cliente/area/cantiere/${widget.idCantiere}/spese');

      final res = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (res.statusCode < 200 || res.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare le spese.';
        });
        return;
      }

      final decoded = jsonDecode(res.body);
      final list = _extractList(decoded);

      setState(() {
        _spese = list.map((e) => SpesaDto.fromJson(e)).toList();
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
      final v = decoded['spese'] ?? decoded['items'] ?? decoded['data'] ?? decoded['list'];
      if (v is List) return v;
    }
    return const [];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Spese')),
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
              : _spese.isEmpty
                  ? const Center(child: Text('Nessuna spesa disponibile.'))
                  : ListView.separated(
                      padding: const EdgeInsets.all(8),
                      itemCount: _spese.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, i) {
                        final s = _spese[i];
                        return ListTile(
                          leading: const Icon(Icons.money),
                          title: Text(
                            '${s.descrizione}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text('${s.data}\nImporto: ${s.importoFormatted}'),
                          trailing: const Icon(Icons.chevron_right),
                        );
                      },
                    ),
    );
  }
}

class SpesaDto {
  SpesaDto({
    required this.data,
    required this.descrizione,
    required this.importo,
  });

  final String data;
  final String descrizione;
  final double importo;

  String get importoFormatted => importo.toStringAsFixed(2).replaceAll('.', ',');

  factory SpesaDto.fromJson(Map<String, dynamic> json) {
    String parseString(dynamic v) => v == null ? '' : v.toString();

    double parseDouble(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) {
        final normalized = v.replaceAll('.', '').replaceAll(',', '.');
        return double.tryParse(normalized) ?? 0.0;
      }
      return 0.0;
    }

    final data = parseString(json['data'] ?? json['giorno'] ?? json['date'] ?? json['timestamp']);
    final descrizione = parseString(
      json['descrizione'] ?? json['description'] ?? json['note'] ?? json['causale'] ?? json['nome'],
    );
    final importo = parseDouble(json['importo'] ?? json['amount'] ?? json['totale'] ?? json['costo'] ?? 0);

    return SpesaDto(data: data, descrizione: descrizione.isEmpty ? 'Spesa' : descrizione, importo: importo);
  }
}
