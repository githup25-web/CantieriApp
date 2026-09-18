import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../cantieri/cantiere_dettaglio_screen.dart';

class FotoScreen extends StatefulWidget {
  const FotoScreen({super.key, required this.idCantiere, required this.palette});

  final int idCantiere;
  final CantierePalette palette;

  @override
  State<FotoScreen> createState() => _FotoScreenState();
}

class _FotoScreenState extends State<FotoScreen> {
  bool _isLoading = false;
  String? _error;

  List<FotoDto> _foto = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _foto = const [];
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
      final uri = Uri.parse('$baseUrl/cliente/area/cantiere/${widget.idCantiere}/foto');

      final res = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (res.statusCode < 200 || res.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare le foto.';
        });
        return;
      }

      final decoded = jsonDecode(res.body);
      final list = _extractList(decoded);

      setState(() {
        _foto = list.map((e) => FotoDto.fromJson(e)).toList();
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
      final v = decoded['foto'] ?? decoded['items'] ?? decoded['data'] ?? decoded['list'];
      if (v is List) return v;
    }
    return const [];
  }

  int _crossAxisCount(double width) {
    // Smartphone: 2
    // Tablet: 3
    // Large tablet/landscape: 4
    if (width >= 900) return 4;
    if (width >= 600) return 3;
    return 2;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Foto avanzamento'),
        backgroundColor: widget.palette.container.withOpacity(0.65),
        foregroundColor: widget.palette.onContainer,
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
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ),
                )
              : _foto.isEmpty
                  ? const Center(child: Text('Nessuna foto disponibile.'))
                  : LayoutBuilder(
                      builder: (context, constraints) {
                        final crossAxisCount = _crossAxisCount(constraints.maxWidth);

                        return RefreshIndicator(
                          onRefresh: _load,
                          child: GridView.builder(
                            padding: const EdgeInsets.all(12),
                            itemCount: _foto.length,
                            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: crossAxisCount,
                              mainAxisSpacing: 12,
                              crossAxisSpacing: 12,
                              childAspectRatio: 1.02,
                            ),
                            itemBuilder: (context, i) {
                              final f = _foto[i];

                              return InkWell(
                                borderRadius: BorderRadius.circular(16),
                                onTap: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                  builder: (_) => FullscreenFotoScreen(
                                        idCantiere: widget.idCantiere,
                                        foto: f,
                                        palette: widget.palette,
                                      ),
                                    ),
                                  );
                                },
                                child: Card(
                                  elevation: 0.5,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                  clipBehavior: Clip.antiAlias,
                                  child: Padding(
                                    padding: const EdgeInsets.all(10),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Expanded(
                                          child: ClipRRect(
                                            borderRadius: BorderRadius.circular(12),
                                            child: f.url == null || f.url!.trim().isEmpty
                                                ? Container(
                                                    color: widget.palette.container.withOpacity(0.25),
                                                    alignment: Alignment.center,
                                                    child: const Text('—'),
                                                  )
                                                : _FadeInImage(
                                                    url: f.url!,
                                                    placeholderColor: widget.palette.container.withOpacity(0.25),
                                                    primaryColor: widget.palette.primary,
                                                  ),
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        Text(
                                          f.data,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: Theme.of(context).textTheme.bodySmall,
                                        ),
                                      ],
                                    ),
                                  ),
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

class _FadeInImage extends StatefulWidget {
  const _FadeInImage({
    required this.url,
    required this.placeholderColor,
    required this.primaryColor,
  });

  final String url;
  final Color placeholderColor;
  final Color primaryColor;

  @override
  State<_FadeInImage> createState() => _FadeInImageState();
}

class _FadeInImageState extends State<_FadeInImage> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  bool _started = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 260),
    );
    _opacity = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: Image.network(
        widget.url,
        fit: BoxFit.cover,
        loadingBuilder: (context, child, progress) {
          if (progress == null) {
            if (!_started) {
              _started = true;
              _controller.forward();
            }
            return child;
          }

          return Container(
            color: widget.placeholderColor,
            alignment: Alignment.center,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(widget.primaryColor),
            ),
          );
        },
        errorBuilder: (context, error, stack) {
          return Container(
            color: widget.placeholderColor,
            alignment: Alignment.center,
            child: const Text('Immagine non disponibile'),
          );
        },
      ),
    );
  }
}

class FullscreenFotoScreen extends StatelessWidget {
  const FullscreenFotoScreen({
    super.key,
    required this.idCantiere,
    required this.foto,
    required this.palette,
  });

  final int idCantiere;
  final FotoDto foto;
  final CantierePalette palette;

  @override
  Widget build(BuildContext context) {
    final url = foto.url;

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(
              child: url == null || url.trim().isEmpty
                  ? const Center(
                      child: Text(
                        'Immagine non disponibile.',
                        style: TextStyle(color: Colors.white70),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : InteractiveViewer(
                      child: Center(
                        child: Image.network(
                          url,
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stack) {
                            return const Center(
                              child: Text(
                                'Immagine non disponibile.',
                                style: TextStyle(color: Colors.white70),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
            ),
            Positioned(
              top: 12,
              left: 12,
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: palette.container.withOpacity(0.16),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close_rounded),
                label: const Text('Chiudi'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class FotoDto {
  FotoDto({required this.data, required this.url});

  final String data;
  final String? url;

  factory FotoDto.fromJson(Map<String, dynamic> json) {
    String parseString(dynamic v) => v == null ? '' : v.toString();
    final data = parseString(
      json['data'] ?? json['created_at'] ?? json['timestamp'] ?? json['giorno'] ?? json['date'],
    );

    final path = parseString(
      json['url'] ?? json['path'] ?? json['file'] ?? json['immagine'] ?? json['image'],
    );
    final url = path.trim().isEmpty ? null : path.trim();

    return FotoDto(data: data, url: url);
  }
}
