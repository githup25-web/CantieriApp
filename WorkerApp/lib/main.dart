import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'core/api_client.dart';
import 'features/auth/login_page.dart';
import 'presentation/screens/home/home_page.dart';
import 'presentation/screens/splash/splash_screen.dart';

void main() {
  ApiClient.init();
  runApp(const WorkerApp());
}

class WorkerApp extends StatelessWidget {
  const WorkerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WorkerApp',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      initialRoute: '/',
      routes: {
        '/': (context) => const SplashScreen(),
        '/login': (context) => const LoginPage(),
        '/home': (context) => const HomePage(),
      },
    );
  }
}
