import '../../core/api_client.dart';

class FotoService {
  static final _dio = ApiClient.dio;

  static Future<List<dynamic>> listByCantiere(String cantiereId) async {
    final res = await _dio.get("/foto/by-cantiere/$cantiereId");
    return res.data as List<dynamic>;
  }
}
