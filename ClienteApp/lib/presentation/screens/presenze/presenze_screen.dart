import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class PresenzeScreen extends StatefulWidget {
  const PresenzeScreen({super.key, required this.idCantiere});

  final int idCantiere;

  @override
  State<PresenzeScreen> createState() => _PresenzeScreenState();
}

class _PresenzeScreenState extends State<PresenzeScreen> {
  bool _isLoading = false;
  String? _error;

  List<PresenzaDto> _presenze = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _presenze = const [];
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
          Uri.parse('$baseUrl/cliente/area/cantiere/${widget.idCantiere}/presenze');

      final res = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (res.statusCode < 200 || res.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare le presenze.';
        });
        return;
      }

      final decoded = jsonDecode(res.body);
      final list = _extractList(decoded);

      setState(() {
        _presenze = list.map((e) => PresenzaDto.fromJson(e)).toList();
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
      final v = decoded['presenze'] ?? decoded['items'] ?? decoded['data'] ?? decoded['list'];
      if (v is List) return v;
    }
    return const [];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Presenze')),
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
              : _presenze.isEmpty
                  ? const Center(child: Text('Nessuna presenza disponibile.'))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(8),
                        itemCount: _presenze.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, i) {
                          final p = _presenze[i];
                          return ListTile(
                            leading: Icon(_iconForOre(p.ore)),
                            title: Text(
                              '${p.data}',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            subtitle: Text('Ore: ${p.ore}\nOperai: ${p.operai}'),
                            trailing: const Icon(Icons.chevron_right),
                          );
                        },
                      ),
                    ),
    );
  }

  IconData _iconForOre(int ore) {
    if (ore >= 8) return Icons.verified;
    if (ore >= 4) return Icons.timelapse;
    return Icons.hourglass_empty;
  }
}

class PresenzaDto {
  PresenzaDto({required this.data, required this.ore, required this.operai});

  final String data;
  final int ore;
  final int operai;

  factory PresenzaDto.fromJson(Map<String, dynamic> json) {
    String parseString(dynamic v) => v == null ? '' : v.toString();
    int parseInt(dynamic v) {
      if (v is int) return v;
      if (v is double) return v.round();
      if (v is String) return int.tryParse(v) ?? 0;
      return 0;
    }

    final data = parseString(json['data'] ?? json['giorno'] ?? json['date'] ?? json['timestamp']);
    final ore = parseInt(json['ore'] ?? json['hours'] ?? json['tot_ore'] ?? json['totale_ore']);
    final operai = parseInt(json['operai'] ?? json['numero_operai'] ?? json['workers'] ?? json['tot_operai']);

    return PresenzaDto(data: data, ore: ore, operai: operai);
  }
}
