import '../../core/api_client.dart';

class PresenzeService {
  static final _dio = ApiClient.dio;

  static Future<List<dynamic>> listByCantiere(String cantiereId) async {
    final res = await _dio.get("/presenze/by-cantiere/$cantiereId");
    return res.data as List<dynamic>;
  }
}
