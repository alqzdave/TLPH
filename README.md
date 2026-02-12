# TLPH - Tagaytay Liquid PH - DENR PROJECT

Welcome to the TLPH project! A comprehensive web application for managing tourism, agriculture, fisheries, forestry, wildlife, and environmental services in the Philippines.

## 📋 Project Overview

TLPH is a full-stack web application designed for the Department of Environment and Natural Resources (DENR) to streamline the management of environmental permits, licenses, services, and inventory tracking. The system supports multiple user roles including super admins, national admins, regional admins, municipal admins, and regular users.

### 🌐 Web Details

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Backend**: Flask (Python 3.x)
- **Database**: Firebase Realtime Database
- **Authentication**: Firebase Authentication
- **Storage**: Firebase Cloud Storage
- **Payment Gateway**: Xendit Payment Integration
- **Email Service**: Flask-Mail with Gmail SMTP
- **Host**: 0.0.0.0 (accessible on all network interfaces)
- **Port**: 5000
- **Debug Mode**: Enabled (Development)

### 🛠️ Technology Stack

```
- Flask 3.0.0 - Web Framework
- Firebase Admin SDK 6.4.0 - Backend Firebase Integration
- Pyrebase4 4.7.1 - Frontend Firebase Integration
- Flask-SQLAlchemy 3.1.1 - ORM
- Flask-Mail 0.9.1 - Email Service
- Xendit 2.9.0 - Payment Processing
- ReportLab 4.0.4 - PDF Generation
- Python-dotenv 1.0.0 - Environment Management
- Requests 2.31.0 - HTTP Library
```

## ✨ Features

### User Management
- Multi-level user authentication (Super Admin, National, Regional, Municipal, User)
- Secure signup and login with Firebase Authentication
- Profile management and user dashboard

### License & Permit Management
- Environment permits
- Fisheries licenses
- Forestry permits
- Livestock permits
- Wildlife permits
- Farm permits
- Application tracking and approval workflow

### Services
- Seminar registration and management
- Service request processing
- Municipal service dashboard

### Inventory Management
- Stock tracking and management
- Stock history and reporting
- User inventory management

### Transaction Management
- Transaction history tracking
- Payment processing with Xendit
- Payment success/failure handling
- Transaction status updates

### Application Routes
- **Main Routes**: Authentication, home, dashboard
- **API Routes**: User management, data operations
- **Municipal Routes**: Municipal admin dashboard
- **Service Routes**: Service management
- **Payment Routes**: Payment processing and verification
- **Permit Routes**: Various permit applications
- **Inventory Routes**: Stock management

## Getting Started

### Prerequisites
```bash
Python 3.8+
pip (Python package manager)
Firebase account
Xendit account (for payments)
Gmail account (for email services)
```

### Installation

1. Clone the repository
```bash
git clone https://github.com/alqzdave/TLPH.git
cd TLPH
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables
Create a `.env` file in the root directory with the following:
```env
SECRET_KEY=your-secret-key
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-app-password
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
XENDIT_API_KEY=your-xendit-api-key
XENDIT_PUBLIC_KEY=your-xendit-public-key
```

4. Set up Firebase credentials
- Download your Firebase service account key as `firebase-credentials.json`
- Place it in the root directory

5. Run the application
```bash
python app.py
```

6. Access the application
```
http://localhost:5000
```

## 👥 Contributors

This project is made possible by the dedicated efforts of the following contributors:

### Development Team

| Name | Role | Email | GitHub | Remarks |
|------|------|-------|--------|--------|
| Mark Dave Alquiza | Team Lead | markdavemarasiganalquiza@gmail.com | [@alqzdave](https://github.com/alqzdave) |
| Aerone John Grefalda | Frontend Developer | grefaldaaeronejohn01@gmail.com | [@Aerone01](https://github.com/Aerone01) |
| John Cedric Acapulco | Frontend Developer | acapulcojohncedric66@gmail.com | [@Cheezzyy1](https://github.com/Cheezzyy1) |
| Jhon Carlo Jimenez | Backend Developer | jimenez.jhoncarlo@minsu.edu.ph | [@kly-njz](https://github.com/kly-njz) | masarap |
| John Mark Pagaduan | Fullcharge Developer | pagaduanjohnmark29@gmail.com | [@johnmark009](https://github.com/johnmark009) |
| Huriecane Ivan Ganio | Q/A, Developer | hurieganio@gmail.com | [@Huriecane](https://github.com/Huriecane) |

### Special Thanks

Special thanks to the **DENR TLPH Team** for their support and guidance throughout the development of this project.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines
- Follow the existing code style and structure
- Write descriptive commit messages
- Test your changes thoroughly before submitting
- Update documentation as needed
- Ensure all Firebase and payment integrations are properly tested

## 📁 Project Structure

```
TLPH/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── firebase_config.py              # Firebase initialization
├── transaction_storage.py          # Transaction management
├── requirements.txt                # Python dependencies
├── firebase-credentials.json       # Firebase service account key
│
├── routes/                         # Application routes
│   ├── main_routes.py             # Authentication & main pages
│   ├── api_routes.py              # API endpoints
│   ├── municipal_routes.py        # Municipal admin routes
│   ├── service_routes.py          # Service management
│   ├── payments_routes.py         # Payment processing
│   ├── permits_routes.py          # Permit applications
│   ├── environment_routes.py      # Environment permits
│   ├── fisheries_routes.py        # Fisheries licenses
│   ├── forest_routes.py           # Forest permits
│   ├── livestock_routes.py        # Livestock permits
│   ├── wildlife_routes.py         # Wildlife permits
│   ├── farm_routes.py             # Farm permits
│   └── seminar_routes.py          # Seminar management
│
├── templates/                      # HTML templates
│   ├── user/                      # User interface templates
│   ├── municipal/                 # Municipal admin templates
│   ├── national/                  # National admin templates
│   ├── regional/                  # Regional admin templates
│   └── super-admin/               # Super admin templates
│
├── static/                         # Static files
│   ├── css/                       # Stylesheets
│   ├── js/                        # JavaScript files
│   ├── images/                    # Image assets
│   └── uploads/                   # User uploaded files
│
├── data/                          # Data storage
│   └── transactions.json          # Transaction cache
│
└── models/                        # Data models
```

## 🔐 Security Features

- Firebase Authentication with secure token management
- Environment variable configuration for sensitive data
- Secure file upload and storage
- Role-based access control (RBAC)
- HTTPS ready for production deployment
- Payment processing with Xendit secure API

## 🚀 Deployment

### Local Development
```bash
python app.py
# Application runs on http://localhost:5000
```

### Production Deployment
1. Set `debug=False` in `app.py`
2. Configure production environment variables
3. Use a production WSGI server (e.g., Gunicorn)
4. Set up HTTPS with SSL certificates
5. Configure Firebase for production
6. Set up Xendit production API keys

## 📧 Email Configuration

The application uses Gmail SMTP for sending emails. To set up:

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password
3. Add credentials to `.env`:
   ```
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Setup Guides

For detailed setup instructions for specific services:

- [Firebase Setup Guide](FIREBASE_SETUP_GUIDE.md)
- [Firebase Setup Instructions](FIREBASE_SETUP.md)
- [Xendit Payment Integration](XENDIT_SETUP.md)

## 📞 Contact & Support

For questions, issues, or support, please:

- **Issue Tracker**: [Open an issue on GitHub](https://github.com/alqzdave/TLPH/issues)
- **Lead Developer**: Mark Dave Alquiza  
  📧 markdavemarasiganalquiza@gmail.com
- **Repository**: [https://github.com/alqzdave/TLPH](https://github.com/alqzdave/TLPH)
- **Organization**: DENR TLPH Team

### Reporting Bugs
When reporting bugs, please include:
- Detailed description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Screenshots (if applicable)
- Browser and OS information

## 🔧 Troubleshooting

## 🔧 Troubleshooting

### Common Issues

- **Port already in use**: 
  ```bash
  # Change the port in app.py or kill the process
  netstat -ano | findstr :5000
  taskkill /PID <process_id> /F
  ```

- **Firebase connection issues**: 
  - Verify credentials in `.env` file
  - Check `firebase-credentials.json` is in root directory
  - Ensure Firebase project is properly configured

- **Missing dependencies**: 
  ```bash
  pip install -r requirements.txt
  ```

- **Email not sending**:
  - Verify Gmail App Password is correct
  - Check MAIL_USERNAME and MAIL_PASSWORD in `.env`
  - Ensure Gmail account has 2FA enabled

- **Payment integration issues**:
  - Verify Xendit API keys are correct
  - Check if using correct environment (test/production)
  - Review Xendit webhook configuration

- **File upload errors**:
  - Check Firebase Storage permissions
  - Verify storage bucket configuration
  - Ensure file size limits are not exceeded

## 📊 API Endpoints

The application provides various API endpoints for:
- User registration and authentication
- Application management
- Transaction processing
- Inventory management
- Payment processing
- File uploads and downloads

## 🎯 Future Enhancements

- [ ] Mobile application (iOS/Android)
- [ ] Advanced analytics dashboard
- [ ] Automated report generation
- [ ] SMS notifications
- [ ] Multi-language support
- [ ] Offline mode capability
- [ ] Enhanced search and filtering
- [ ] Data export functionality

## 📖 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Firebase Documentation](https://firebase.google.com/docs)
- [Xendit API Documentation](https://xendit.io/docs)
- [Python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## 🏆 Acknowledgments

- **DENR (Department of Environment and Natural Resources)** - Project sponsor and stakeholder
- **Firebase** - Backend infrastructure and authentication
- **Xendit** - Payment gateway integration
- **Flask Community** - Web framework and ecosystem
- All contributors and team members who made this project possible

## 📜 Version History

- **v1.0** - Initial release with core features
  - User authentication and authorization
  - License and permit management
  - Payment integration
  - Inventory tracking
  - Transaction management

---

**Made with ❤️ by the DENR TLPH Development Team**

For more information or to contribute, visit our [GitHub Repository](https://github.com/alqzdave/TLPH)
