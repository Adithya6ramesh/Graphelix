# Take It Down - User Management System

## Overview
The Take It Down system now features a secure user management system with three role types and controlled access.

## User Roles

### 👤 Victim
- Can register publicly without admin approval
- Can report harmful content
- Can view their own submitted cases
- Access to case history and status tracking

### 👮 Officer
- Can only be created by admins
- Can review and manage submitted cases
- Can update case statuses (pending, under review, approved, rejected)
- Access to case dashboard and filtering

### 👑 Admin
- Can register with special admin ID (1234)
- Can create any type of user account (victim, officer, admin)
- Full system access including user management
- Can view system statistics and manage all cases

## Registration Process

### Public Registration
1. Visit the application at http://localhost:8080
2. Click "Register"
3. Choose between:
   - **Victim**: Standard user registration
   - **Admin**: Requires admin ID "1234"
4. Fill in email and password
5. If admin selected, enter admin ID: `1234`

### Admin-Created Users
1. Login as admin
2. Go to Admin Dashboard
3. Click "Create User"
4. Fill in user details and select role
5. User account is created immediately

## Security Features

1. **Role-based Access Control**: Each endpoint checks user permissions
2. **Secure Admin Registration**: Admin registration requires special ID
3. **JWT Authentication**: All API calls use JWT tokens
4. **CORS Protection**: Configured for specific frontend origins
5. **No Public Officer Creation**: Officers can only be created by admins

## API Endpoints

### Public Endpoints
- `POST /api/auth/register` - Public registration (victim/admin with ID)
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info

### Admin Endpoints
- `POST /api/admin/create-user` - Create any user type
- `GET /api/admin/users` - List all users
- `GET /api/admin/stats` - System statistics
- `POST /api/admin/users/{id}/role` - Update user role

### Case Management
- `POST /api/cases/` - Submit new case (victims)
- `GET /api/cases/my-cases` - Get user's cases (victims)
- `GET /api/cases/all` - Get all cases (officers/admins)
- `PUT /api/cases/{id}/status` - Update case status (officers/admins)

## Initial Setup

### Option 1: Create Admin via Registration
1. Visit http://localhost:8080
2. Register with admin role using ID: `1234`

### Option 2: Create Admin via Script
```bash
python create_admin.py
```

## Server Commands

### Start Backend (Port 8000)
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### Start Frontend (Port 8080)
```bash
python serve_frontend.py
```

## Environment
- Backend: http://localhost:8000
- Frontend: http://localhost:8080
- API Docs: http://localhost:8000/docs

## Troubleshooting

### CORS Errors
- Ensure both servers are running on correct ports
- Check that CORS origins in main.py include your frontend URL

### Authentication Errors
- Check that JWT tokens are being sent correctly
- Verify user has appropriate role for the endpoint

### Database Errors
- Run `python create_admin.py` to ensure database is initialized
- Check that all database tables are created properly

## Data Flow

1. **User Registration**:
   - Public users can create victim accounts
   - Admin ID required for admin accounts
   - Officers created only by existing admins

2. **Authentication**:
   - Login returns JWT token
   - Token included in all subsequent requests
   - Token expires based on configuration

3. **Role-based Features**:
   - UI adapts based on user role
   - Different dashboard views per role
   - Endpoint access controlled by role

## Security Considerations

- Admin ID (1234) should be changed for production
- Use HTTPS in production environments
- Implement rate limiting for public endpoints
- Regular security audits recommended
- Consider implementing 2FA for admin accounts
