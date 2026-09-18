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
      final foto = await FotoService.listByCantiere(widget.cantiereId);
      setState(() => _foto = foto);
    } catch (e) {
      setState(() => _error = 'Errore caricamento foto: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  String _resolveUrl(String url) {
    if (url.startsWith('http')) return url;
    final base = ApiClient.dio.options.baseUrl.replaceAll(RegExp(r'/$'), '');
    return '$base$url';
  }

  int _crossAxisCount(double width) {
    if (width >= 900) return 4;
    if (width >= 600) return 3;
    return 2;
  }

  void _showDetail(Map<String, dynamic> foto) {
    final url = foto['url'] as String? ?? '';
    final resolvedUrl = url.isNotEmpty ? _resolveUrl(url) : null;
    final timestamp = (foto['timestamp'] as String? ?? '').split('T');
    final dateStr = timestamp.isNotEmpty ? timestamp[0] : '—';
    final timeStr =
        timestamp.length > 1 ? timestamp[1].split('.').first : '';
    final workerId = foto['worker_id'] as String? ?? '—';
    final descrizione = foto['descrizione'] as String?;

    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Immagine fullscreen-ish
            ClipRRect(
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(20)),
              child: resolvedUrl == null
                  ? Container(
                      height: 220,
                      color: Colors.grey.shade200,
                      alignment: Alignment.center,
                      child: const Icon(Icons.image_not_supported, size: 48),
                    )
                  : InteractiveViewer(
                      child: Image.network(
                        resolvedUrl,
                        height: 280,
                        width: double.infinity,
                        fit: BoxFit.cover,
                        loadingBuilder: (context, child, progress) =>
                            progress == null
                                ? child
                                : SizedBox(
                                    height: 220,
                                    child: Center(
                                      child: CircularProgressIndicator(
                                        value: progress.expectedTotalBytes !=
                                                null
                                            ? progress.cumulativeBytesLoaded /
                                                progress.expectedTotalBytes!
                                            : null,
                                      ),
                                    ),
                                  ),
                        errorBuilder: (context, _, __) => Container(
                          height: 220,
                          color: Colors.grey.shade200,
                          alignment: Alignment.center,
                          child: const Icon(Icons.broken_image, size: 48),
                        ),
                      ),
                    ),
            ),
            // Dettagli
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _DetailRow(icon: Icons.calendar_today_rounded, text: dateStr),
                  if (timeStr.isNotEmpty)
                    _DetailRow(icon: Icons.access_time_rounded, text: timeStr),
                  _DetailRow(icon: Icons.person_rounded, text: workerId),
                  if (descrizione != null && descrizione.isNotEmpty)
                    _DetailRow(
                        icon: Icons.notes_rounded, text: descrizione),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Chiudi'),
              ),
            ),
          ],
        ),
      ),
    );
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
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!,
                  style: TextStyle(
                      color: Theme.of(context).colorScheme.error)),
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

    if (_foto.isEmpty) {
      return RefreshIndicator(
        onRefresh: _load,
        child: const CustomScrollView(
          slivers: [
            SliverFillRemaining(
              child: Center(child: Text('Nessuna foto disponibile')),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final crossAxisCount = _crossAxisCount(constraints.maxWidth);

          return GridView.builder(
            padding: const EdgeInsets.all(12),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 0.88,
            ),
            itemCount: _foto.length,
            itemBuilder: (context, index) {
              final foto = _foto[index] as Map<String, dynamic>;
              final url = foto['url'] as String? ?? '';
              final resolvedUrl =
                  url.isNotEmpty ? _resolveUrl(url) : null;
              final timestamp =
                  (foto['timestamp'] as String? ?? '').split('T');
              final dateStr =
                  timestamp.isNotEmpty ? timestamp[0] : '—';

              return GestureDetector(
                onTap: () => _showDetail(foto),
                child: Card(
                  elevation: 1,
                  clipBehavior: Clip.antiAlias,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Thumbnail
                      Expanded(
                        child: resolvedUrl == null
                            ? Container(
                                color: Colors.grey.shade200,
                                alignment: Alignment.center,
                                child: const Icon(Icons.image_not_supported),
                              )
                            : _FadingNetworkImage(url: resolvedUrl),
                      ),
                      // Footer
                      Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 6),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              dateStr,
                              style: Theme.of(context)
                                  .textTheme
                                  .labelSmall,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            Text(
                              foto['worker_id'] as String? ?? '',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .outline,
                                  ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

// ── Widget ausiliari ──────────────────────────────────────────────────────────

class _FadingNetworkImage extends StatelessWidget {
  const _FadingNetworkImage({required this.url});

  final String url;

  @override
  Widget build(BuildContext context) {
    return Image.network(
      url,
      fit: BoxFit.cover,
      loadingBuilder: (context, child, progress) {
        if (progress == null) return child;
        return Container(
          color: Colors.grey.shade100,
          alignment: Alignment.center,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            value: progress.expectedTotalBytes != null
                ? progress.cumulativeBytesLoaded /
                    progress.expectedTotalBytes!
                : null,
          ),
        );
      },
      errorBuilder: (context, _, __) => Container(
        color: Colors.grey.shade200,
        alignment: Alignment.center,
        child: const Icon(Icons.broken_image, color: Colors.grey),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: Theme.of(context).colorScheme.outline),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}
