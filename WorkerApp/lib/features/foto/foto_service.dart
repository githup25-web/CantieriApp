import 'package:dio/dio.dart';
import '../../core/api_client.dart';

class FotoService {
  static final dio = ApiClient.dio;

  static Future<Map<String, dynamic>> upload({
    required String cantiereId,
    required String workerId,
    required String filePath,
    String? descrizione,
  }) async {
    final formData = FormData.fromMap({
      "cantiere_id": cantiereId,
      "worker_id": workerId,
      if (descrizione != null && descrizione.isNotEmpty) "descrizione": descrizione,
      "file": await MultipartFile.fromFile(filePath),
    });

    final res = await dio.post("/foto/upload", data: formData);
    return res.data;
  }

  static Future<List<dynamic>> listByCantiere(String cantiereId) async {
    final res = await dio.get("/foto/by-cantiere/$cantiereId");
    return res.data;
  }
}
