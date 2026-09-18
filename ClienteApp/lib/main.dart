import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/theme/app_theme.dart';
import 'core/api_client.dart';
import 'features/auth/login_page.dart';
import 'features/cliente/cliente_page.dart';
import 'presentation/screens/splash/splash_screen.dart';
import 'presentation/screens/login/code_login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);
  ApiClient.init();
  runApp(const ClienteApp());
}

class ClienteApp extends StatelessWidget {
  const ClienteApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ClienteApp',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      initialRoute: '/',
      routes: {
        '/': (context) => const SplashScreen(),
        '/login': (context) => const CodeLoginScreen(),
        '/login-email': (context) => const LoginPage(),
        // FASE 8: ClientePage è la UI principale del cliente
        '/home': (context) => const ClientePage(),
        '/cliente': (context) => const ClientePage(),
      },
    );
  }
}
