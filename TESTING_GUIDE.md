# Testing Guide - Secure User Management System

## 🚀 System Overview
✅ **Backend**: http://localhost:8000
✅ **Frontend**: http://localhost:8080
✅ **API Docs**: http://localhost:8000/docs

## 📋 Test Scenarios

### 1. **Victim Registration** (Public)
- Visit: http://localhost:8080
- Click "Register"
- Select: "👤 Victim (Report Content)"
- Enter email and password
- ✅ Should register successfully

### 2. **Admin Registration** (With ID)
- Visit: http://localhost:8080
- Click "Register"
- Select: "👑 Admin (Manage System)"
- Admin ID field appears
- Enter admin ID: `1234`
- Enter email and password
- ✅ Should register successfully

### 3. **Admin Creating Users**
- Login as admin
- Go to Admin Dashboard
- Click "➕ Create User"
- Can create: Victim, Officer, Admin
- ✅ Should create any role

## 🔒 Security Features

### ✅ **Role-Based Access**
- Victims: Can only report cases
- Officers: Can only be created by admins
- Admins: Full system access

### ✅ **Secure Registration**
- Public can only create victim accounts
- Admin accounts require ID "1234"
- Officers cannot be created publicly

### ✅ **No CORS Errors**
- Configured for ports 3000 and 8080
- Proper headers included
- Authentication working

## 🧪 Quick Test Commands

### Test Backend API Directly
```bash
# Test registration endpoint
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Test admin registration
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123","admin_id":"1234"}'
```

## 🎯 Expected Behavior

1. **Registration Dropdown**: Only shows Victim and Admin
2. **Admin ID Field**: Appears only when Admin is selected
3. **Validation**: Admin ID must be "1234"
4. **Admin Dashboard**: Shows "Create User" button
5. **User Creation**: Admins can create all role types
6. **Security**: No officer creation without admin

## 🔧 Troubleshooting

### Port Issues
- Kill processes: `taskkill /PID [PID] /F`
- Check ports: `netstat -ano | findstr :8080`

### CORS Issues
- Verify both servers running
- Check network tab in browser
- Confirm origins in main.py

### Authentication Issues
- Check JWT token in requests
- Verify user roles in database
- Test with API docs at /docs
