import '../../core/api_client.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthService {
  static final dio = ApiClient.dio;
  static final storage = const FlutterSecureStorage();

  static Future<bool> login(String email, String password) async {
    final res = await dio.post("/auth/login", data: {
      "email": email,
      "password": password,
    });

    await storage.write(key: "access_token", value: res.data["access_token"]);
    await storage.write(key: "refresh_token", value: res.data["refresh_token"]);
    return true;
  }

  static Future<Map<String, dynamic>> me() async {
    final res = await dio.get("/auth/me");
    return res.data;
  }
}
