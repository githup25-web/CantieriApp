import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'core/api_client.dart';
import 'features/auth/login_page.dart';
import 'features/auth/register_page.dart';
import 'features/auth/otp_page.dart';
import 'presentation/screens/home/home_page.dart';
import 'presentation/screens/splash/splash_screen.dart';

void main() {
  ApiClient.init();
  runApp(const CantieriApp());
}

class CantieriApp extends StatelessWidget {
  const CantieriApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CantieriApp',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      initialRoute: '/',
      routes: {
        '/': (context) => const SplashScreen(),
        '/login': (context) => const LoginPage(),
        '/register': (context) => const RegisterPage(),
        // La verify route riceve email come argomento
        '/verify': (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          final email = args is Map ? args['email']?.toString() ?? '' : '';
          return OTPPage(email: email);
        },
        '/home': (context) => const HomePage(),
      },
    );
  }
}
