import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  // Supporto --dart-define=API_BASE_URL=... per configurare l'URL in produzione
  static const String _defaultBaseUrl = "http://127.0.0.1:8000";
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: _defaultBaseUrl,
  );

  static final Dio dio = Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
    ),
  );

  static final storage = const FlutterSecureStorage();

  static void init() {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await storage.read(key: "access_token");
          if (token != null) {
            options.headers["Authorization"] = "Bearer $token";
          }
          handler.next(options);
        },
      ),
    );
  }
}
