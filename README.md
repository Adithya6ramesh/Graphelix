# 🛡️ Graphelix - Harmful Content Reporting System

A comprehensive web application for reporting and managing harmful online content, built with FastAPI and modern web technologies.

## 🚀 Features

- **Role-Based Access Control**: Victim, Officer, and Admin roles with different capabilities
- **Smart Deduplication**: Prevents duplicate reports using URL normalization and content fingerprinting
- **Real-Time Processing**: Instant case submission with immediate feedback
- **Audit Trail**: Complete event history for all case activities
- **Rate Limiting**: Built-in protection against abuse
- **Dark Theme UI**: Modern, professional interface
- **Comprehensive Testing**: 53+ test cases covering all functionality

## 🏗️ Architecture

### Backend (FastAPI)
- **Authentication**: JWT-based with bcrypt password hashing
- **Database**: SQLite with SQLAlchemy ORM and Alembic migrations
- **API**: RESTful endpoints with automatic documentation
- **Services**: Modular design with URL normalization and deduplication

### Frontend (HTML/JavaScript)
- **Responsive Design**: Mobile-friendly dark theme
- **Role-Based UI**: Different interfaces for different user types
- **Real-Time Feedback**: Instant status updates and error handling
- **CORS Enabled**: Secure cross-origin communication

## 📊 Database Schema

- **Users**: Email, hashed passwords, roles, timestamps
- **Cases**: URLs/hashes, descriptions, states, due dates, assignees
- **Case Events**: Audit trail with timestamps and user actions
- **Deduplication**: Content fingerprints for duplicate detection

## 🔧 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Adithya6ramesh/Graphelix.git
   cd Graphelix
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database**
   ```bash
   alembic upgrade head
   ```

4. **Start the backend server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Start the frontend server**
   ```bash
   python serve_frontend.py
   ```

6. **Access the application**
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8000/docs

## 👥 User Roles

### 🙋‍♀️ Victims
- Submit harmful content reports
- Provide URLs or file hashes
- Add detailed descriptions
- Track submission status

### 👮‍♀️ Officers
- Review submitted cases
- Investigate reported content
- Update case statuses
- Manage case assignments

### 👑 Admins
- Full system access
- User management
- System configuration
- Analytics and reporting

## 🧪 Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/ -v
```

Test coverage includes:
- Authentication and authorization
- Database models and relationships
- URL normalization algorithms
- Deduplication logic
- API endpoints and validation
- Error handling and edge cases

## 📚 API Endpoints

- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication
- `GET /api/auth/me` - Current user info
- `POST /api/cases/` - Submit new case
- `GET /api/cases/` - List cases (role-based)

## 🔒 Security Features

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: bcrypt with salt
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Pydantic schemas
- **SQL Injection Protection**: SQLAlchemy ORM
- **CORS Configuration**: Secure cross-origin requests

## 🛠️ Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, bcrypt, PyJWT
- **Database**: SQLite (production-ready alternatives available)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Testing**: pytest, pytest-asyncio
- **Development**: uvicorn, watchfiles

## 📈 Performance

- **Response Time**: < 100ms for most operations
- **Deduplication**: O(1) lookup with hash indexing
- **Rate Limiting**: 100 requests per hour per user
- **Concurrent Users**: Supports multiple simultaneous users

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is part of a hackathon submission and is available for educational purposes.

## 🆘 Support

For issues and questions:
- Check the User Guide (USER_GUIDE.md)
- Review the Quick Reference (QUICK_REFERENCE.md)
- Open an issue on GitHub

---

**Built with ❤️ for protecting digital communities**
