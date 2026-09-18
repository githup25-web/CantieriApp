import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class CodeLoginScreen extends StatefulWidget {
  const CodeLoginScreen({super.key});

  @override
  State<CodeLoginScreen> createState() => _CodeLoginScreenState();
}

class _CodeLoginScreenState extends State<CodeLoginScreen> {
  final _codeController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final codice = _codeController.text.trim();

    final validationError = _validate(codice);
    if (validationError != null) {
      setState(() => _error = validationError);
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      const baseUrl = 'http://localhost:8000';
      final uri = Uri.parse('$baseUrl/cliente/login-codice');

      final res = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: '{"codice":"${codice.replaceAll('"', '\\"')}"}',
      );

      if (res.statusCode >= 200 && res.statusCode < 300) {
        final token = _extractToken(res.body);

        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('jwt_token', token);

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Benvenuto! Accesso confermato.')),
        );

        Navigator.pushReplacementNamed(context, '/home');
        return;
      }

      setState(() {
        _error = 'Codice non valido. Contatta l’azienda.';
      });
    } catch (_) {
      setState(() {
        _error = 'Codice non valido. Contatta l’azienda.';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  String? _validate(String codice) {
    if (codice.isEmpty) return 'Codice non valido. Contatta l’azienda.';
    return null;
  }

  String _extractToken(String body) {
    try {
      final match = RegExp(r'"token"\s*:\s*"([^"]+)"').firstMatch(body);
      if (match != null && match.groupCount >= 1) return match.group(1)!;
    } catch (_) {}

    return body;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(height: 48),
                  Text(
                    'Login',
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _codeController,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _login(),
                    decoration: const InputDecoration(
                      labelText: 'Inserisci il tuo codice di accesso',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: _isLoading ? null : _login,
                    child: _isLoading
                        ? const SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Accedi'),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
