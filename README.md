# TLPH - Tagaytay Liquid PH - DENR PROJECT

Welcome to the TLPH project! A comprehensive web application for managing tourism, agriculture, fisheries, forestry, wildlife, and environmental services in the Philippines.

## Overview

TLPH is a Flask-based web application designed to streamline the management and licensing of various land-based and environmental-related activities in the Philippines. It provides a platform for users to submit applications, track payments, manage seminars, and handle various agricultural and environmental services across different administrative levels (municipal, regional, national, and super-admin).

## Features

- **Multi-role Access Control**: Support for end-users, municipal officials, regional administrators, and super-admins
- **License Management**: Handles licenses for fisheries, forestry, livestock, wildlife, and environmental permits
- **Service Management**: Manages seminars, farm visits, fertilizer services, financial services, and compensation claims
- **Payment Integration**: Integrated with Xendit for payment processing
- **Application Tracking**: Monitor application status and approvals
- **Inventory Management**: Track and manage resources across different municipalities
- **Firebase Authentication**: Secure user authentication with Firebase
- **Responsive Design**: Works on desktop and mobile devices

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/alqzdave/TLPH.git
   cd TLPH
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Create a `.env` file in the root directory
   - Add the following variables (contact the maintainers for actual values):
     ```
     FLASK_ENV=development
     SECRET_KEY=your_secret_key
     FIREBASE_API_KEY=your_firebase_api_key
     FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
     FIREBASE_DATABASE_URL=your_firebase_database_url
     FIREBASE_PROJECT_ID=your_firebase_project_id
     FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
     FIREBASE_MESSAGING_SENDER_ID=your_firebase_sender_id
     XENDIT_API_KEY=your_xendit_api_key
     ```

5. **Run the application**
   ```bash
   python app.py
   ```
   
   The application will be available at `http://localhost:5000`

## Project Structure

```
TLPH/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── firebase_config.py    # Firebase configuration
├── requirements.txt      # Python dependencies
├── routes/               # Route handlers for different features
│   ├── main_routes.py
│   ├── api_routes.py
│   ├── fisheries_routes.py
│   ├── forest_routes.py
│   ├── livestock_routes.py
│   ├── wildlife_routes.py
│   ├── environment_routes.py
│   ├── permits_routes.py
│   ├── service_routes.py
│   ├── seminar_routes.py
│   ├── payments_routes.py
│   └── farm_routes.py
├── models/               # Data models
├── templates/            # HTML templates
│   ├── user/            # User-facing templates
│   ├── municipal/       # Municipal admin templates
│   ├── regional/        # Regional admin templates
│   ├── national/        # National admin templates
│   └── super-admin/     # Super admin templates
└── static/              # Static files (CSS, JS, images)
    ├── css/
    ├── js/
    └── uploads/
```

## Usage

1. Navigate to `http://localhost:5000`
2. Sign up or log in with your Firebase account
3. Choose your role/access level
4. Start managing your applications, licenses, and services

## Dependencies

- **Flask** - Web framework
- **Flask-SQLAlchemy** - ORM and database support
- **Flask-Mail** - Email sending functionality
- **Firebase Admin SDK** - Firebase integration
- **Pyrebase4** - Firebase realtime database access
- **Xendit** - Payment processing
- **python-dotenv** - Environment variable management

See `requirements.txt` for complete list with versions.

## Contributors

This project was developed by:

| Name | Email | Role | Remarks |
|------|-------|------|------|
| Dave Alquiza | markdavemarasiganalquiza@gmail.com | Lead Developer |
| Jhon Carlo Jimenez (kly-njz) | kly-njz@users.noreply.github.com | Developer | Masarap |
| Aerone01 | grefaldaaeronejohn01@gmail.com | Contributor/Dev |
| Cedric | acapulcojohncedric66@gmail.com | Contributor/Dev |
| John Mark Pagaduan | pagaduanjohnmark29@gmail.com | Contributor/Dev |

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Setup Guides

For detailed setup instructions for specific services:

- [Firebase Setup Guide](FIREBASE_SETUP_GUIDE.md)
- [Firebase Setup Instructions](FIREBASE_SETUP.md)
- [Xendit Payment Integration](XENDIT_SETUP.md)

## Contact & Support

For questions, issues, or support, please:

- Open an issue on GitHub
- Contact the lead developer: markdavemarasiganalquiza@gmail.com
- Visit the project repository: https://github.com/alqzdave/TLPH

## Troubleshooting

- **Port already in use**: Change the port in `app.py` or kill the process using port 5000
- **Firebase connection issues**: Verify your credentials in `.env` file
- **Missing dependencies**: Run `pip install -r requirements.txt` again

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Firebase Documentation](https://firebase.google.com/docs)
- [Xendit API Documentation](https://xendit.io/docs)
