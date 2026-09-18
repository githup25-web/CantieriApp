import 'package:flutter/material.dart';
import '../../../features/auth/auth_service.dart';
import '../../../features/presenze/presenze_service.dart';

class PresenzePage extends StatefulWidget {
  const PresenzePage({super.key});

  @override
  State<PresenzePage> createState() => _PresenzePageState();
}

class _PresenzePageState extends State<PresenzePage> {
  final _cantiereController = TextEditingController();
  String? _workerId;
  bool _loading = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    final user = await AuthService.me();
    setState(() => _workerId = user["id"]);
  }

  Future<void> _checkin() async {
    if (_workerId == null || _cantiereController.text.isEmpty) return;
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      await PresenzeService.checkin(
        workerId: _workerId!,
        cantiereId: _cantiereController.text,
      );
      setState(() => _message = "Check-in registrato");
    } catch (e) {
      setState(() => _message = "Errore check-in: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _checkout() async {
    if (_workerId == null || _cantiereController.text.isEmpty) return;
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      await PresenzeService.checkout(
        workerId: _workerId!,
        cantiereId: _cantiereController.text,
      );
      setState(() => _message = "Check-out registrato");
    } catch (e) {
      setState(() => _message = "Errore check-out: $e");
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _cantiereController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Presenze")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _cantiereController,
              decoration: const InputDecoration(
                labelText: "ID Cantiere",
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _loading ? null : _checkin,
              child: const Text("Check-in"),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _loading ? null : _checkout,
              child: const Text("Check-out"),
            ),
            const SizedBox(height: 24),
            if (_loading) const Center(child: CircularProgressIndicator()),
            if (_message != null)
              Text(
                _message!,
                style: TextStyle(
                  color: _message!.startsWith("Errore") ? Colors.red : Colors.green,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
