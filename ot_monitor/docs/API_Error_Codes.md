# OT Monitor — API Error Code Reference

All errors are returned as JSON: `{"detail": "message"}` with the matching HTTP status code.

---

## 401 Unauthorized

Returned from any protected endpoint when not logged in or session has expired.

| Trigger | Detail |
|---|---|
| Calling a protected route with no session cookie | `Authentication required` |
| Session cookie is expired or tampered | `Invalid or expired session` |
| Wrong username or password at `/auth/login` | `Invalid credentials` |

**Fix — log in first:**
```bash
curl -c cookies.txt -X POST http://ot-monitor.local:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"OTAdmin2024"}'
```
Then pass `-b cookies.txt` on every subsequent request.

Session lifetime is set in `config.yaml → auth.session_expire_minutes` (default 60 min).

---

## 403 Forbidden

| Trigger | Detail |
|---|---|
| Logged in as `nurse` (viewer) but calling an admin-only endpoint | `Admin access required for this action` |

Admin-only endpoints:
- `POST /alarms/{id}/acknowledge`
- `POST /settings/thresholds`
- `POST /settings/reload`
- `GET  /settings/users`
- `POST /settings/users`
- `DELETE /settings/users/{username}`

---

## 400 Bad Request

| Trigger | Detail |
|---|---|
| Invalid date format in `/history` or `/export/csv` | `Invalid datetime: ...` |
| Add user — missing username or password | `username and password are required` |
| Add user — invalid role value | `role must be 'admin' or 'viewer'` |
| Delete user — trying to delete your own account | `Cannot delete your own account` |
| Delete user — would remove the last admin | `Cannot remove the last admin account` |

---

## 404 Not Found

| Trigger | Detail |
|---|---|
| Acknowledge a non-existent alarm ID | `Alarm not found` |
| Delete a username that does not exist | `User '{name}' not found` |

---

## 409 Conflict

| Trigger | Detail |
|---|---|
| Add user with a username that already exists | `User '{name}' already exists` |

---

## 503 Service Unavailable

| Trigger | Detail |
|---|---|
| Backend still starting up (config not yet loaded) | `Server not ready` |

---

## Endpoint Access Summary

| Endpoint | Method | Auth required |
|---|---|---|
| `/` | GET | None — serves dashboard HTML |
| `/ws` | WS | None — WebSocket live feed |
| `/health` | GET | None |
| `/history` | GET | None |
| `/alarms` | GET | None |
| `/settings/thresholds` | GET | None |
| `/auth/login` | POST | None |
| `/auth/logout` | POST | None |
| `/auth/me` | GET | Any logged-in user |
| `/export/csv` | GET | Any logged-in user |
| `/alarms/{id}/acknowledge` | POST | Admin only |
| `/settings/thresholds` | POST | Admin only |
| `/settings/reload` | POST | Admin only |
| `/settings/users` | GET | Admin only |
| `/settings/users` | POST | Admin only |
| `/settings/users/{username}` | DELETE | Admin only |

---

## Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `OTAdmin2024` |
| Viewer | `nurse` | `OTNurse2024` |

Change these in `config.yaml → auth.users` before deploying.

---

*OT Monitor Backend — June 2026*
