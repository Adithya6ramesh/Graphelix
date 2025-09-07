# 🛡️ Take It Down - User Guide

## 📖 Overview
**Graphelix** is a comprehensive content moderation system designed to help users report harmful content and enable officers to review and take action on these reports. The system provides role-based access with different interfaces for victims, officers, and administrators.

---

## 🌐 Accessing the System

### URLs:
- **Frontend Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Backend API**: http://localhost:8000

---

## 👥 User Roles

### 🙋‍♀️ **Victim (Content Reporter)**
- Can register and submit reports about harmful content
- Can track their submitted cases
- Primary interface: Content submission form

### 👮‍♀️ **Officer (Content Reviewer)**
- Can review submitted cases
- Can approve or reject cases
- Can view case details and make decisions
- Primary interface: Case review dashboard

### 👑 **Admin (System Administrator)**
- Full system access
- Can manage users and cases
- Can view system statistics
- Primary interface: Administrative dashboard

---

## 🚀 Getting Started Guide

### Step 1: Registration
1. **Open the website** at http://localhost:3000
2. **Click "Register here"** link below the login form
3. **Fill in the registration form**:
   - **Email**: Your email address (username)
   - **Password**: Choose a secure password
   - **Role**: Select your role:
     - 🙋‍♀️ **Victim** if you want to report harmful content
     - 👮‍♀️ **Officer** if you're a content moderator
     - 👑 **Admin** if you're a system administrator
4. **Click "Register"** button
5. **Wait for confirmation** message

### Step 2: Login
1. **Enter your credentials**:
   - **Username**: The email you registered with
   - **Password**: Your password
2. **Click "Login"** button
3. **System will redirect** you to your role-specific interface

---

## 📋 User Interface Guide by Role

### 🙋‍♀️ **For Victims (Reporting Harmful Content)**

#### After Login, You'll See:
- **User info bar** showing your email and role
- **Report Harmful Content form** with fields:

#### How to Submit a Report:
1. **Choose content type**:
   - **URL**: Enter the web address of harmful content
   - **OR File Hash**: Enter SHA256 hash of a harmful file
2. **Add description**: Explain why the content is harmful
3. **Click "🚨 Submit Report"**

#### What Happens Next:
- **New Case**: System creates a new case with unique ID
- **Duplicate Detection**: If content already reported, links to existing case
- **Status Messages**: Real-time feedback on submission
- **Case Details**: View case ID, status, and tracking information

#### Example Report Submission:
```
URL: https://example.com/harmful-content
Description: This page contains hate speech targeting minorities and should be removed immediately.
```

### 👮‍♀️ **For Officers (Reviewing Cases)**

#### After Login, You'll See:
- **Officer Dashboard** with case review tools
- **Pending Cases** list
- **Case action buttons**

#### How to Review Cases:
1. **View pending cases** in the dashboard
2. **Click on a case** to see details
3. **Review content** and description
4. **Make decision**:
   - **Approve**: Take down the content
   - **Reject**: Dismiss the case
   - **Investigate**: Mark for further review

#### Officer Interface Features:
- 📊 **Case Statistics**
- 🔍 **Search and Filter Cases**
- 📝 **Add Review Notes**
- ⚡ **Quick Actions**

### 👑 **For Admins (System Management)**

#### After Login, You'll See:
- **Administrative Dashboard**
- **System Overview**
- **User Management Tools**

#### Admin Capabilities:
- 👥 **Manage Users**: Add, edit, or remove users
- 📊 **View Statistics**: System usage and case metrics
- 🔧 **System Configuration**: Modify system settings
- 📈 **Reports**: Generate system reports

---

## 🔧 Key Features Explained

### 🔄 **Deduplication System**
- **Automatic Detection**: System detects if content already reported
- **URL Normalization**: Different URL formats point to same content
- **Hash Matching**: File hashes ensure exact duplicate detection
- **Linking**: Multiple reports link to same case

### 🛡️ **Security Features**
- **JWT Authentication**: Secure token-based login
- **Role-Based Access**: Users only see appropriate interface
- **Password Hashing**: Secure password storage
- **HTTPS Ready**: Production security measures

### 📊 **Case Management**
- **Unique Case IDs**: Every report gets trackable ID
- **Status Tracking**: Open, In Review, Approved, Rejected
- **Due Dates**: Automatic 7-day review deadlines
- **Audit Trail**: Complete history of case actions

### ⚡ **Real-Time Features**
- **Live Status Updates**: Immediate feedback on actions
- **Auto-Refresh**: Content updates without page reload
- **Error Handling**: Clear error messages and recovery

---

## 📱 Step-by-Step Usage Examples

### Example 1: Victim Reporting Harmful Website
```
1. Register as "Victim"
2. Login with credentials
3. Enter URL: "https://badsite.com/hate-content"
4. Description: "Contains racial slurs and hate speech"
5. Submit Report
6. Receive Case ID: #12345
7. Track case status
```

### Example 2: Officer Reviewing Case
```
1. Register as "Officer"
2. Login with credentials
3. View pending cases dashboard
4. Select Case #12345
5. Review content and description
6. Make decision: "Approve for takedown"
7. Add notes: "Violates community guidelines"
8. Submit decision
```

### Example 3: Admin Managing System
```
1. Register as "Admin"
2. Login with credentials
3. View system dashboard
4. Check user statistics
5. Review case metrics
6. Generate monthly report
```

---

## 🚨 Troubleshooting

### Common Issues:

#### "Incorrect email or password"
- **Check spelling** in email and password
- **Ensure account exists** - register first if needed
- **Try password reset** (if implemented)

#### "Network Error"
- **Check servers are running**:
  - Backend: http://localhost:8000
  - Frontend: http://localhost:3000
- **Refresh the page**
- **Check internet connection**

#### "Access Denied"
- **Verify your role** matches the action
- **Re-login** to refresh permissions
- **Contact admin** if role needs changing

#### Page Not Loading
- **Clear browser cache**
- **Disable browser extensions**
- **Try different browser**
- **Check console for errors** (F12)

---

## 🔗 API Documentation

### For Developers:
Visit http://localhost:8000/docs for interactive API documentation including:
- **Authentication endpoints**
- **Case submission APIs**
- **User management APIs**
- **Response schemas**
- **Try-it-out features**

---

## 📞 Support & Contact

### Getting Help:
1. **Check this guide** for common solutions
2. **View API docs** at http://localhost:8000/docs
3. **Check browser console** for error messages
4. **Contact system administrator**

### System Status:
- **Backend Status**: Check http://localhost:8000
- **Frontend Status**: Check http://localhost:3000
- **Database**: SQLite (local file)

---

## 🎯 Best Practices

### For Victims:
- **Be specific** in descriptions
- **Include evidence** when possible
- **One report per issue** (system handles duplicates)
- **Check status regularly**

### For Officers:
- **Review thoroughly** before decisions
- **Add detailed notes** for transparency
- **Handle cases promptly** (7-day deadline)
- **Follow guidelines** consistently

### For Admins:
- **Monitor system health** regularly
- **Review user feedback**
- **Update policies** as needed
- **Backup data** regularly

---

## 🔮 Advanced Features

### URL Normalization:
```
These URLs are treated as the same:
- http://example.com/page
- https://example.com/page
- https://www.example.com/page
- https://example.com/page/
```

### File Hash Reporting:
```
SHA256 Hash Format:
abcd1234ef567890abcd1234ef567890abcd1234ef567890abcd1234ef567890
(64 hexadecimal characters)
```

### Case Linking:
- Multiple reports → Single case
- Reduces duplicate work
- Maintains report history
- Notifies all reporters

---

## 🏁 Quick Start Checklist

- [ ] ✅ **Servers Running**: Backend (8000) + Frontend (3000)
- [ ] 📝 **Account Created**: Email + Password + Role
- [ ] 🔑 **Logged In**: Credentials working
- [ ] 🎯 **Interface Loaded**: Role-appropriate dashboard
- [ ] 🚀 **Ready to Use**: Submit reports or review cases

**You're all set! Start reporting harmful content or reviewing cases based on your role.**

---

*Last Updated: September 7, 2025*
*System Version: 1.0.0*
