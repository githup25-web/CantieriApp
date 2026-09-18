import '../../core/api_client.dart';

class FotoService {
  static final dio = ApiClient.dio;

  static Future<List<dynamic>> listByCantiere(String cantiereId) async {
    final res = await dio.get("/foto/by-cantiere/$cantiereId");
    return res.data;
  }
}
