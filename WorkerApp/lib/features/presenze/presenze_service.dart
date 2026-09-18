import '../../core/api_client.dart';

class PresenzeService {
  static final dio = ApiClient.dio;

  static Future<Map<String, dynamic>> checkin({
    required String workerId,
    required String cantiereId,
  }) async {
    final res = await dio.post("/presenze/checkin", data: {
      "worker_id": workerId,
      "cantiere_id": cantiereId,
    });
    return res.data;
  }

  static Future<Map<String, dynamic>> checkout({
    required String workerId,
    required String cantiereId,
  }) async {
    final res = await dio.post("/presenze/checkout", data: {
      "worker_id": workerId,
      "cantiere_id": cantiereId,
    });
    return res.data;
  }
}
