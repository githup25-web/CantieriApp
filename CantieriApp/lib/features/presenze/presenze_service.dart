import '../../core/api_client.dart';

class PresenzeService {
  static final dio = ApiClient.dio;

  static Future<List<dynamic>> listByCantiere(String cantiereId) async {
    final res = await dio.get("/presenze/by-cantiere/$cantiereId");
    return res.data;
  }
}
