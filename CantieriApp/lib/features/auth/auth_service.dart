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

  static Future<Map<String, dynamic>> register(String email, String password) async {
    final res = await dio.post("/auth/register", data: {
      "email": email,
      "password": password,
    });
    return res.data;
  }

  static Future<Map<String, dynamic>> verify(String email, String otp) async {
    final res = await dio.post("/auth/verify", data: {
      "email": email,
      "otp": otp,
    });
    return res.data;
  }

  static Future<Map<String, dynamic>> resendOtp(String email) async {
    final res = await dio.post("/auth/resend-otp", data: {
      "email": email,
    });
    return res.data;
  }

  static Future<Map<String, dynamic>> me() async {
    final res = await dio.get("/auth/me");
    return res.data;
  }
}
