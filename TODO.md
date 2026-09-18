# TODO - Registrazione Utente + Verifica Email (OTP)

## Backend
- [x] 1. Update `app/models/user.py` - Add status, otp, roles, tenant_ids fields + OtpInfo model + UserStatus enum
- [x] 2. Update `app/core/config.py` - Add SMTP, OTP settings, deep link scheme, restrict CORS
- [x] 3. Create `app/services/email_service.py` - Async email sending via SMTP (HTML + text)
- [x] 4. Create `app/services/otp_service.py` - OTP generation, validation, rate limiting, security logging
- [x] 5. Rewrite `app/routes/auth.py` - New endpoints: register, verify, resend-otp, login (gated)
- [x] 6. Update `app/tests/conftest.py` - Add users/otps to cleanup collections
- [x] 7. Create `app/tests/test_auth_otp.py` - Automated tests for OTP flow

## Frontend (CantieriApp)
- [x] 8. Update `CantieriApp/lib/features/auth/auth_service.dart` - Add register, verify, resendOtp methods
- [x] 9. Create `CantieriApp/lib/features/auth/register_page.dart` - Registration screen with validation
- [x] 10. Create `CantieriApp/lib/features/auth/otp_page.dart` - OTP entry, countdown, resend, deep link
- [x] 11. Update `CantieriApp/lib/main.dart` - Add /register and /verify routes
- [x] 12. Update `CantieriApp/pubspec.yaml` - Add app_links for deep link support

## Verification
- [ ] 13. Run backend tests (pytest)
- [ ] 14. Run flutter analyze
