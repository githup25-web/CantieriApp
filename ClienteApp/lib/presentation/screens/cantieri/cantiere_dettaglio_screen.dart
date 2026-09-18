import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../foto/foto_screen.dart';

class CantiereDettaglioScreen extends StatefulWidget {
  const CantiereDettaglioScreen({super.key, required this.idCantiere});

  final int idCantiere;

  @override
  State<CantiereDettaglioScreen> createState() => _CantiereDettaglioScreenState();
}

class _CantiereDettaglioScreenState extends State<CantiereDettaglioScreen> {
  bool _isLoading = false;
  String? _error;

  CantiereDettaglioDto? _cantiere;
  List<TimelineEventoDto> _timeline = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('jwt_token');

      if (token == null || token.trim().isEmpty) {
        setState(() {
          _error = 'Sessione non valida. Effettua il login.';
          _cantiere = null;
          _timeline = const [];
        });
        return;
      }

      const baseUrl = 'http://localhost:8000';

      final cantiereUri =
          Uri.parse('$baseUrl/cliente/area/cantiere/${widget.idCantiere}');
      final timelineUri = Uri.parse(
          '$baseUrl/cliente/area/cantiere/${widget.idCantiere}/timeline');

      final cantiereRes = await http.get(
        cantiereUri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (cantiereRes.statusCode < 200 || cantiereRes.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare il dettaglio del cantiere.';
          _cantiere = null;
          _timeline = const [];
        });
        return;
      }

      final timelineRes = await http.get(
        timelineUri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (timelineRes.statusCode < 200 || timelineRes.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare la timeline.';
          _cantiere = null;
          _timeline = const [];
        });
        return;
      }

      final cantiereDecoded = _decodeJson(cantiereRes.body);
      final timelineDecoded = _decodeJson(timelineRes.body);

      final cantiereDto =
          CantiereDettaglioDto.fromJson(_extractFirstMap(cantiereDecoded));
      final timelineList = _extractTimelineList(timelineDecoded)
          ?.whereType<Map<String, dynamic>>()
          .map(TimelineEventoDto.fromJson)
          .toList();

      setState(() {
        _cantiere = cantiereDto;
        _timeline = timelineList ?? const [];
      });
    } catch (_) {
      setState(() {
        _error = 'Errore di rete. Riprova.';
        _cantiere = null;
        _timeline = const [];
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  dynamic _decodeJson(String body) {
    try {
      if (body.trim().isEmpty) return null;
      return jsonDecode(body);
    } catch (_) {
      return null;
    }
  }

  Map<String, dynamic> _extractFirstMap(dynamic decoded) {
    if (decoded is Map<String, dynamic>) return decoded;
    if (decoded is Map) return decoded.cast<String, dynamic>();
    if (decoded is List && decoded.isNotEmpty && decoded.first is Map) {
      return (decoded.first as Map).cast<String, dynamic>();
    }
    return const {};
  }

  List<dynamic>? _extractTimelineList(dynamic decoded) {
    if (decoded == null) return null;
    if (decoded is List) return decoded;
    if (decoded is Map<String, dynamic>) {
      final v = decoded['timeline'] ??
          decoded['eventi'] ??
          decoded['items'] ??
          decoded['data'];
      if (v is List) return v;
    }
    return null;
  }

  CantierePalette _palette(BuildContext context, String stato) {
    final s = stato.toLowerCase().trim();
    final scheme = Theme.of(context).colorScheme;

    if (s.contains('complet') || s.contains('finito') || s.contains('chius')) {
      return CantierePalette(
        primary: const Color(0xFF2E7D32),
        container: const Color(0xFFEDF7ED),
        onContainer: const Color(0xFF1B5E20),
        progressTrack: scheme.surfaceVariant,
      );
    }
    if (s.contains('in corso') ||
        s.contains('attiv') ||
        s.contains('lavor') ||
        s.contains('build') ||
        s.contains('avanz')) {
      return CantierePalette(
        primary: const Color(0xFF1565C0),
        container: const Color(0xFFE3F2FD),
        onContainer: const Color(0xFF0D47A1),
        progressTrack: scheme.surfaceVariant,
      );
    }
    if (s.contains('sosp') || s.contains('paused') || s.contains('fermo')) {
      return CantierePalette(
        primary: const Color(0xFF6D4C41),
        container: const Color(0xFFF5F0EB),
        onContainer: const Color(0xFF4E342E),
        progressTrack: scheme.surfaceVariant,
      );
    }

    return CantierePalette(
      primary: scheme.primary,
      container: scheme.primaryContainer,
      onContainer: scheme.onPrimaryContainer,
      progressTrack: scheme.surfaceVariant,
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = _cantiere?.nomeCantiere ?? 'Dettaglio Cantiere';
    final stato = _cantiere?.stato ?? '';
    final palette = _palette(context, stato);

    final progress = (_cantiere?.percentualeAvanzamento ?? 0).clamp(0, 100) / 100;

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        backgroundColor: palette.container.withOpacity(0.65),
        foregroundColor: palette.onContainer,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      _error!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : _cantiere == null
                  ? const Center(child: Text('Nessun dato disponibile.'))
                  : LayoutBuilder(
                      builder: (context, constraints) {
                        final isTablet = constraints.maxWidth >= 600;
                        final padding = isTablet ? 20.0 : 16.0;

                        return SingleChildScrollView(
                          padding: EdgeInsets.all(padding),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Card(
                                elevation: 0,
                                color:
                                    Theme.of(context).colorScheme.surfaceContainerHighest,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(18),
                                ),
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        _cantiere!.nomeCantiere,
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleLarge,
                                      ),
                                      const SizedBox(height: 10),
                                      Wrap(
                                        spacing: 10,
                                        runSpacing: 8,
                                        crossAxisAlignment:
                                            WrapCrossAlignment.center,
                                        children: [
                                          _InfoChip(
                                            icon: Icons.place_rounded,
                                            label: _cantiere!.indirizzo,
                                          ),
                                          _StatusChip(
                                            status: _cantiere!.stato,
                                            icon: Icons.construction_rounded,
                                            palette: palette,
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 14),
                                      Text(
                                        'Avanzamento',
                                        style:
                                            Theme.of(context).textTheme.titleSmall,
                                      ),
                                      const SizedBox(height: 8),
                                      Row(
                                        children: [
                                          Expanded(
                                            child: ClipRRect(
                                              borderRadius:
                                                  BorderRadius.circular(12),
                                              child: LinearProgressIndicator(
                                                value: progress,
                                                minHeight: 10,
                                                backgroundColor: palette.progressTrack,
                                                valueColor:
                                                    AlwaysStoppedAnimation<Color>(
                                                  palette.primary,
                                                ),
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 12),
                                          Text(
                                            '${_cantiere!.percentualeAvanzamento}%',
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium
                                                ?.copyWith(
                                                    color: palette.primary,
                                                    fontWeight: FontWeight.w800),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(height: 18),

                              Text(
                                'Timeline lavori',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 10),

                              if (_timeline.isEmpty)
                                const Text('Nessun evento disponibile.')
                              else
                                Column(
                                  children: _timeline
                                      .map(
                                        (e) => Padding(
                                          padding:
                                              const EdgeInsets.only(bottom: 12),
                                          child: TimelineCard(
                                            evento: e,
                                            palette: palette,
                                          ),
                                        ),
                                      )
                                      .toList(),
                                ),

                              const SizedBox(height: 18),
                              Text(
                                'Azioni',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 10),

                              Wrap(
                                spacing: 12,
                                runSpacing: 12,
                                children: [
                                  FilledButton.icon(
                                    onPressed: () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) => FotoScreen(
                                            idCantiere: widget.idCantiere,
                                            palette: palette,
                                          ),
                                        ),
                                      );
                                    },
                                    icon: const Icon(Icons.photo_album_rounded),
                                    label: const Text('Foto avanzamento'),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                            ],
                          ),
                        );
                      },
                    ),
    );
  }
}

class TimelineCard extends StatelessWidget {
  const TimelineCard({
    super.key,
    required this.evento,
    required this.palette,
  });

  final TimelineEventoDto evento;
  final CantierePalette palette;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: palette.container.withOpacity(0.55),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              evento.data,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: palette.onContainer.withOpacity(0.85),
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              evento.descrizione,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 18),
      label: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.status,
    required this.icon,
    required this.palette,
  });

  final String status;
  final IconData icon;
  final CantierePalette palette;

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 18, color: palette.primary),
      label: Text(
        status,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              fontWeight: FontWeight.w800,
              color: palette.onContainer,
            ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      backgroundColor: palette.container,
      side: BorderSide(color: palette.primary.withOpacity(0.25)),
    );
  }
}

class CantiereDettaglioDto {
  const CantiereDettaglioDto({
    required this.nomeCantiere,
    required this.indirizzo,
    required this.stato,
    required this.percentualeAvanzamento,
    required this.descrizione,
  });

  final String nomeCantiere;
  final String indirizzo;
  final String stato;
  final int percentualeAvanzamento;
  final String descrizione;

  factory CantiereDettaglioDto.fromJson(Map<String, dynamic> json) {
    int parseInt(dynamic v) {
      if (v is int) return v;
      if (v is double) return v.round();
      if (v is String) return int.tryParse(v) ?? 0;
      return 0;
    }

    String parseString(dynamic v) {
      if (v == null) return '';
      return v.toString();
    }

    return CantiereDettaglioDto(
      nomeCantiere: parseString(json['nome_cantiere'] ?? json['nome'] ?? json['titolo']),
      indirizzo: parseString(json['indirizzo'] ?? json['address']),
      stato: parseString(json['stato'] ?? json['status']),
      percentualeAvanzamento: parseInt(
        json['percentuale_avanzamento'] ?? json['percentuale'] ?? json['progress'],
      ),
      descrizione: parseString(json['descrizione'] ?? json['description'] ?? json['note']),
    );
  }
}

class TimelineEventoDto {
  const TimelineEventoDto({required this.data, required this.descrizione});

  final String data;
  final String descrizione;

  factory TimelineEventoDto.fromJson(Map<String, dynamic> json) {
    String parseString(dynamic v) {
      if (v == null) return '';
      return v.toString();
    }

    return TimelineEventoDto(
      data: parseString(json['data'] ?? json['date'] ?? json['timestamp']),
      descrizione: parseString(
        json['descrizione'] ?? json['descr'] ?? json['description'],
      ),
    );
  }
}

class CantierePalette {
  const CantierePalette({
    required this.primary,
    required this.container,
    required this.onContainer,
    required this.progressTrack,
  });

  final Color primary;
  final Color container;
  final Color onContainer;
  final Color progressTrack;
}
