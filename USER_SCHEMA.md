# User Schema Documentation

## Firestore Collections

### 1. `users` Collection

User documents stored in Firestore.

**Document ID**: Auto-generated or user ID

**Fields**:
```json
{
  "id": "user_abc123",
  "phone_number": "919876543210",
  "name": "John Doe",
  "is_verified": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login_at": "2024-01-15T11:00:00Z"
}
```

**Field Descriptions**:
- `phone_number`: Normalized phone number (no spaces, dashes, etc.)
- `name`: Optional user name (can be updated later)
- `is_verified`: Whether phone number is verified via OTP
- `created_at`: When user account was created
- `last_login_at`: Last successful login timestamp

### 2. `otps` Collection

Temporary OTP storage for authentication.

**Document ID**: Auto-generated

**Fields**:
```json
{
  "id": "otp_xyz789",
  "phone_number": "919876543210",
  "otp": "123456",
  "expires_at": "2024-01-15T10:35:00Z",
  "created_at": "2024-01-15T10:30:00Z",
  "verified": false,
  "attempts": 0,
  "verified_at": null,
  "invalidated_at": null
}
```

**Field Descriptions**:
- `phone_number`: Phone number OTP was sent to
- `otp`: 6-digit OTP code
- `expires_at`: When OTP expires (5 minutes from creation)
- `created_at`: When OTP was created
- `verified`: Whether OTP has been verified
- `attempts`: Number of verification attempts
- `verified_at`: Timestamp when OTP was verified (if verified)
- `invalidated_at`: Timestamp when OTP was invalidated (if invalidated)

## API Endpoints

### POST /auth/send-otp
Send OTP to phone number.

**Request**:
```json
{
  "phone_number": "+91 9876543210"
}
```

**Response**:
```json
{
  "success": true,
  "message": "OTP sent to 919876543210",
  "otp": "123456",  // Remove in production
  "expires_in_minutes": 5
}
```

### POST /auth/verify-otp
Verify OTP and authenticate user.

**Request**:
```json
{
  "phone_number": "+91 9876543210",
  "otp": "123456"
}
```

**Response**:
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "user": {
    "id": "user_abc123",
    "phone_number": "919876543210",
    "name": null,
    "is_verified": true,
    "created_at": "2024-01-15T10:30:00Z",
    "last_login_at": "2024-01-15T11:00:00Z"
  },
  "token": "abc123def456..."
}
```

## Frontend Integration

### Authentication Flow

1. User enters phone number on `/login`
2. Frontend calls `POST /auth/send-otp`
3. User redirected to `/verify-otp?phone=...`
4. User enters OTP
5. Frontend calls `POST /auth/verify-otp`
6. On success, token and user stored in localStorage
7. User redirected to home page

### Session Management

- Token stored in `localStorage.auth_token`
- User data stored in `localStorage.auth_user`
- Header component checks authentication status
- Logout clears localStorage and redirects to login

## Security Considerations

### OTP Security
- OTPs expire after 5 minutes
- Maximum 3 verification attempts per OTP
- OTPs are invalidated after successful verification
- OTPs stored in separate collection (not in user document)

### Phone Number Normalization
- Phone numbers normalized (remove spaces, dashes, etc.)
- Stored in consistent format for lookup

### Production Recommendations
1. **Remove OTP from API response** - Only log in development
2. **Implement SMS service** - Use Twilio, AWS SNS, or similar
3. **Add rate limiting** - Prevent OTP spam
4. **Use JWT tokens** - Replace simple token with proper JWT
5. **Add phone number validation** - Validate country codes
6. **Add CAPTCHA** - Prevent automated OTP requests

## Migration Notes

### Existing Reports
- Reports can be linked to users via `user_id` field (future enhancement)
- No breaking changes to existing report schema

### User Creation
- Users created automatically on first OTP verification
- Users updated on subsequent logins (updates `last_login_at`)
