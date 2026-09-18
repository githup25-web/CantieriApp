import '../../core/api_client.dart';

class TaskService {
  static final dio = ApiClient.dio;

  static Future<Map<String, dynamic>> create({
    required String cantiereId,
    required String titolo,
    required String descrizione,
    required String assegnatoA,
    String stato = "in_attesa",
    String? dataScadenza,
  }) async {
    final res = await dio.post("/tasks/create", data: {
      "cantiere_id": cantiereId,
      "titolo": titolo,
      "descrizione": descrizione,
      "assegnato_a": assegnatoA,
      "stato": stato,
      if (dataScadenza != null && dataScadenza.isNotEmpty)
        "data_scadenza": dataScadenza,
    });
    return res.data;
  }

  static Future<List<dynamic>> listByCantiere(String cantiereId) async {
    final res = await dio.get("/tasks/by-cantiere/$cantiereId");
    return res.data;
  }

  static Future<Map<String, dynamic>> update(
    String taskId, {
    String? titolo,
    String? descrizione,
    String? assegnatoA,
    String? stato,
    String? dataScadenza,
  }) async {
    final data = <String, dynamic>{};
    if (titolo != null) data["titolo"] = titolo;
    if (descrizione != null) data["descrizione"] = descrizione;
    if (assegnatoA != null) data["assegnato_a"] = assegnatoA;
    if (stato != null) data["stato"] = stato;
    if (dataScadenza != null) data["data_scadenza"] = dataScadenza;

    final res = await dio.patch("/tasks/update/$taskId", data: data);
    return res.data;
  }
}
