import '../../core/api_client.dart';

class ClienteService {
  static final _dio = ApiClient.dio;

  static Future<Map<String, dynamic>> login(String code) async {
    final res = await _dio.post(
      "/client/login",
      data: {'code': code},
    );
    return res.data as Map<String, dynamic>;
  }

  /// Elenca i cantieri assegnati al cliente autenticato (FASE 8).
  static Future<List<dynamic>> getCantieri() async {
    final res = await _dio.get("/cliente/area/cantieri");
    return res.data as List<dynamic>;
  }

  /// Dettaglio cantiere corrente (dal token).
  static Future<Map<String, dynamic>> getCantiereStato() async {
    final res = await _dio.get("/cliente/area/cantiere");
    return res.data as Map<String, dynamic>;
  }

  /// Avanzamento lavori (task + percentuale) del cantiere corrente.
  static Future<Map<String, dynamic>> getAvanzamento() async {
    final res = await _dio.get("/cliente/area/avanzamento");
    return res.data as Map<String, dynamic>;
  }

  /// Foto di avanzamento del cantiere corrente.
  static Future<List<dynamic>> getFoto() async {
    final res = await _dio.get("/cliente/area/foto");
    final data = res.data as Map<String, dynamic>;
    return (data['foto'] as List<dynamic>?) ?? const [];
  }

  /// Presenze del cantiere corrente.
  static Future<List<dynamic>> getPresenze() async {
    final res = await _dio.get("/cliente/area/presenze");
    final data = res.data as Map<String, dynamic>;
    return (data['presenze'] as List<dynamic>?) ?? const [];
  }

  /// Notifiche del cliente (FASE 8).
  static Future<List<dynamic>> getNotifiche() async {
    final res = await _dio.get("/cliente/area/notifiche");
    final data = res.data as Map<String, dynamic>;
    return (data['notifiche'] as List<dynamic>?) ?? const [];
  }

  /// Spese del cantiere corrente.
  static Future<Map<String, dynamic>> getSpese() async {
    final res = await _dio.get("/cliente/area/spese");
    return res.data as Map<String, dynamic>;
  }

  /// Documenti del cantiere corrente.
  static Future<List<dynamic>> getDocumenti() async {
    final res = await _dio.get("/cliente/area/documenti");
    final data = res.data as Map<String, dynamic>;
    return (data['documenti'] as List<dynamic>?) ?? const [];
  }
}
