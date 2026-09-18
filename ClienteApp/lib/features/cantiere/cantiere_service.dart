/// Calcola l'avanzamento di un cantiere dai task restituiti dal backend.
class AvanzamentoResult {
  const AvanzamentoResult({
    required this.totale,
    required this.completati,
    required this.inCorso,
    required this.inAttesa,
  });

  final int totale;
  final int completati;
  final int inCorso;
  final int inAttesa;

  /// Valore 0.0 – 1.0 per LinearProgressIndicator.
  double get percentuale => totale == 0 ? 0.0 : completati / totale;

  /// Percentuale intera 0 – 100 per visualizzazione.
  int get percentualeInt => (percentuale * 100).round();
}

class CantiereService {
  /// Calcola avanzamento dai task già scaricati (evita una doppia chiamata HTTP).
  static AvanzamentoResult calcolaAvanzamento(List<dynamic> tasks) {
    int completati = 0, inCorso = 0, inAttesa = 0;

    for (final raw in tasks) {
      final task = raw as Map<String, dynamic>;
      final stato = task['stato'] as String? ?? '';
      switch (stato) {
        case 'completato':
          completati++;
        case 'in_corso':
          inCorso++;
        default:
          inAttesa++;
      }
    }

    return AvanzamentoResult(
      totale: tasks.length,
      completati: completati,
      inCorso: inCorso,
      inAttesa: inAttesa,
    );
  }
}
