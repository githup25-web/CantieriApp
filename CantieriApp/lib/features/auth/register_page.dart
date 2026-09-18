import 'package:flutter/material.dart';
import 'auth_service.dart';
import 'otp_page.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final email = TextEditingController();
  final password = TextEditingController();
  final confirmPassword = TextEditingController();
  bool privacyAccepted = false;
  bool _loading = false;
  String? _emailError;
  String? _passwordError;
  String? _confirmError;
  String? _privacyError;

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    confirmPassword.dispose();
    super.dispose();
  }

  bool _validate() {
    setState(() {
      _emailError = null;
      _passwordError = null;
      _confirmError = null;
      _privacyError = null;
    });

    bool valid = true;

    // Validazione email
    if (email.text.trim().isEmpty) {
      _emailError = "Inserisci l'email";
      valid = false;
    } else if (!RegExp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$").hasMatch(email.text.trim())) {
      _emailError = "Email non valida";
      valid = false;
    }

    // Validazione password (min 8 caratteri)
    if (password.text.isEmpty) {
      _passwordError = "Inserisci la password";
      valid = false;
    } else if (password.text.length < 8) {
      _passwordError = "La password deve avere almeno 8 caratteri";
      valid = false;
    }

    // Conferma password
    if (confirmPassword.text.isEmpty) {
      _confirmError = "Conferma la password";
      valid = false;
    } else if (confirmPassword.text != password.text) {
      _confirmError = "Le password non coincidono";
      valid = false;
    }

    // Privacy
    if (!privacyAccepted) {
      _privacyError = "Devi accettare la privacy policy";
      valid = false;
    }

    return valid;
  }

  Future<void> _register() async {
    if (!_validate()) return;

    setState(() => _loading = true);
    try {
      final data = await AuthService.register(email.text.trim(), password.text);
      if (!mounted) return;

      // Naviga alla schermata OTP
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => OTPPage(email: email.text.trim()),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      String msg = "Errore durante la registrazione";
      if (e.toString().contains("already registered")) {
        msg = "Email già registrata";
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg)),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Registrazione")),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.construction, size: 64, color: Colors.blueGrey),
                const SizedBox(height: 16),
                Text(
                  "Crea il tuo account",
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  "Registrati per iniziare a usare CantieriApp",
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 32),

                // Email
                TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: "Email",
                    prefixIcon: const Icon(Icons.email),
                    border: const OutlineInputBorder(),
                    errorText: _emailError,
                  ),
                ),
                const SizedBox(height: 16),

                // Password
                TextField(
                  controller: password,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: "Password",
                    prefixIcon: const Icon(Icons.lock),
                    border: const OutlineInputBorder(),
                    errorText: _passwordError,
                    helperText: "Minimo 8 caratteri",
                  ),
                ),
                const SizedBox(height: 16),

                // Conferma password
                TextField(
                  controller: confirmPassword,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: "Conferma password",
                    prefixIcon: const Icon(Icons.lock_outline),
                    border: const OutlineInputBorder(),
                    errorText: _confirmError,
                  ),
                ),
                const SizedBox(height: 16),

                // Checkbox privacy
                CheckboxListTile(
                  value: privacyAccepted,
                  onChanged: (val) => setState(() => privacyAccepted = val ?? false),
                  title: const Text("Accetto la privacy policy"),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                  secondary: _privacyError != null
                      ? Text(
                          _privacyError!,
                          style: const TextStyle(color: Colors.red, fontSize: 12),
                        )
                      : null,
                ),
                const SizedBox(height: 16),

                // Pulsante registrati
                ElevatedButton(
                  onPressed: _loading ? null : _register,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: _loading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text("Registrati"),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
