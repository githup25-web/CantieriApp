import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class NotificheScreen extends StatefulWidget {
  const NotificheScreen({super.key});

  @override
  State<NotificheScreen> createState() => _NotificheScreenState();
}

class _NotificheScreenState extends State<NotificheScreen> {
  bool _isLoading = false;
  String? _error;

  List<NotificaDto> _notifiche = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _notifiche = const [];
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
      final uri = Uri.parse('$baseUrl/cliente/notifiche');

      final res = await http.get(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (res.statusCode < 200 || res.statusCode >= 300) {
        setState(() {
          _error = 'Impossibile caricare le notifiche.';
        });
        return;
      }

      final decoded = jsonDecode(res.body);
      final list = _extractList(decoded);

      setState(() {
        _notifiche = list.map((e) => NotificaDto.fromJson(e)).toList();
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
      final v =
          decoded['notifiche'] ?? decoded['items'] ?? decoded['data'] ?? decoded['list'];
      if (v is List) return v;
    }
    return const [];
  }

  _TipoStyle _styleForTipo(BuildContext context, String tipo) {
    final t = tipo.toLowerCase();
    final scheme = Theme.of(context).colorScheme;

    if (t == 'info' || t == 'information') {
      return _TipoStyle(
        icon: Icons.info_rounded,
        color: const Color(0xFF64B5F6),
        bg: const Color(0xFFE3F2FD),
      );
    }
    if (t == 'warning' || t == 'warn') {
      return _TipoStyle(
        icon: Icons.warning_rounded,
        color: const Color(0xFFFFB74D),
        bg: const Color(0xFFFFF3E0),
      );
    }
    if (t == 'alert' || t == 'error' || t == 'danger') {
      return _TipoStyle(
        icon: Icons.error_rounded,
        color: scheme.error,
        bg: const Color(0xFFFFEBEE),
      );
    }

    return _TipoStyle(
      icon: Icons.notifications_rounded,
      color: scheme.primary,
      bg: scheme.surfaceVariant,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifiche'),
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
              : _notifiche.isEmpty
                  ? const Center(child: Text('Nessuna notifica disponibile.'))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(12),
                        itemCount: _notifiche.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, i) {
                          final n = _notifiche[i];
                          final style = _styleForTipo(context, n.tipo);

                          return Dismissible(
                            key: ValueKey('${n.titolo}-${n.data}-$i'),
                            direction: DismissDirection.endToStart,
                            background: _DismissBackground(color: style.bg),
                            onDismissed: (_) {
                              setState(() {
                                _notifiche.removeAt(i);
                              });
                            },
                            child: _NotificaCard(
                              notifica: n,
                              style: style,
                              onTap: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) =>
                                        NotificaDettaglioScreen(notifica: n),
                                  ),
                                );
                              },
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}

class _NotificaCard extends StatelessWidget {
  const _NotificaCard({
    required this.notifica,
    required this.style,
    required this.onTap,
  });

  final NotificaDto notifica;
  final _TipoStyle style;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Card(
      elevation: 0.5,
      color: style.bg,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: style.color.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(style.icon, color: style.color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      notifica.titolo,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      notifica.messaggio,
                      style: Theme.of(context).textTheme.bodyMedium,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      notifica.data,
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: scheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(Icons.chevron_right_rounded, color: scheme.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}

class _DismissBackground extends StatelessWidget {
  const _DismissBackground({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(16),
      ),
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.only(right: 16),
      child: const Icon(Icons.delete_outline_rounded, color: Colors.black54),
    );
  }
}

class _TipoStyle {
  _TipoStyle({
    required this.icon,
    required this.color,
    required this.bg,
  });

  final IconData icon;
  final Color color;
  final Color bg;
}

class NotificaDettaglioScreen extends StatelessWidget {
  const NotificaDettaglioScreen({super.key, required this.notifica});

  final NotificaDto notifica;

  @override
  Widget build(BuildContext context) {
    final hasRif =
        notifica.riferimento != null && notifica.riferimento!.trim().isNotEmpty;
    final hasLink = notifica.link != null && notifica.link!.trim().isNotEmpty;

    final t = notifica.tipo.toLowerCase();
    final scheme = Theme.of(context).colorScheme;

    Color badgeBg = scheme.primary.withOpacity(0.12);
    Color badgeFg = scheme.primary;
    IconData badgeIcon = Icons.info_rounded;

    if (t == 'warning' || t == 'warn') {
      badgeBg = const Color(0xFFFFF3E0);
      badgeFg = const Color(0xFFFFB74D);
      badgeIcon = Icons.warning_rounded;
    } else if (t == 'alert' || t == 'error' || t == 'danger') {
      badgeBg = const Color(0xFFFFEBEE);
      badgeFg = scheme.error;
      badgeIcon = Icons.error_rounded;
    } else if (t == 'info' || t == 'information') {
      badgeBg = const Color(0xFFE3F2FD);
      badgeFg = const Color(0xFF64B5F6);
      badgeIcon = Icons.info_rounded;
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(notifica.titolo),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0.5,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: badgeBg,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Icon(badgeIcon, color: badgeFg),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          notifica.titolo,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _MetaChip(label: 'Data', value: notifica.data),
                      _MetaChip(label: 'Tipo', value: notifica.tipo),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    notifica.messaggioCompleto,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.35),
                  ),
                ],
              ),
            ),
          ),
          if (hasRif) ...[
            const SizedBox(height: 12),
            Card(
              elevation: 0.5,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Text(
                  'Riferimento: ${notifica.riferimento}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ),
          ],
          if (hasLink) ...[
            const SizedBox(height: 12),
            Card(
              elevation: 0.5,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Link:', style: Theme.of(context).textTheme.labelLarge),
                    const SizedBox(height: 8),
                    SelectableText(
                      notifica.link!,
                      maxLines: 8,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(
        '$label: $value',
        style: Theme.of(context).textTheme.labelMedium,
      ),
      avatar: const Icon(Icons.circle, size: 10),
    );
  }
}

class NotificaDto {
  NotificaDto({
    required this.titolo,
    required this.messaggio,
    required this.messaggioCompleto,
    required this.data,
    required this.tipo,
    this.riferimento,
    this.link,
  });

  final String titolo;
  final String messaggio;
  final String messaggioCompleto;
  final String data;
  final String tipo;
  final String? riferimento;
  final String? link;

  factory NotificaDto.fromJson(Map<String, dynamic> json) {
    String parseString(dynamic v) => v == null ? '' : v.toString();

    final tipoRaw =
        parseString(json['tipo'] ?? json['type'] ?? json['categoria'] ?? json['level']);
    final tipo = tipoRaw.trim().isEmpty ? 'info' : tipoRaw.trim();

    final titolo = parseString(json['titolo'] ?? json['title'] ?? json['name']);
    final messaggio =
        parseString(json['messaggio'] ?? json['message'] ?? json['body']);

    final messaggioCompleto = parseString(
      json['messaggio_completo'] ??
          json['full_message'] ??
          json['full'] ??
          json['detail'] ??
          json['descrizione'],
    );

    final data =
        parseString(json['data'] ?? json['date'] ?? json['created_at'] ?? json['timestamp']);

    final riferimento = json['riferimento'] ??
        json['riferimento_cantiere'] ??
        json['cantiere'] ??
        json['reference'];
    final link = json['link'] ?? json['url'];

    return NotificaDto(
      titolo: titolo.trim().isEmpty ? 'Notifica' : titolo.trim(),
      messaggio: messaggio,
      messaggioCompleto:
          messaggioCompleto.trim().isEmpty ? messaggio : messaggioCompleto.trim(),
      data: data,
      tipo: tipo,
      riferimento: riferimento == null ? null : parseString(riferimento),
      link: link == null ? null : parseString(link),
    );
  }
}
