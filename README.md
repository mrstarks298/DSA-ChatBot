# DSA Mentor - AI-Powered Data Structures & Algorithms Learning Assistant

A comprehensive Flask-based web application that provides an intelligent learning companion for mastering Data Structures and Algorithms (DSA) concepts.

## 🚀 Features

### Core Learning Features
- **AI-Powered Q&A**: Get detailed explanations of DSA concepts using Groq AI
- **Semantic Search**: Find relevant content from a curated DSA knowledge base
- **Practice Problems**: Access a database of DSA practice questions
- **Video Recommendations**: Get relevant video tutorials for each topic
- **PDF Export**: Download your learning sessions as PDF documents

### User Experience
- **Google OAuth Authentication**: Secure login with Google accounts
- **Chat Interface**: Interactive conversation-style learning
- **Thread Management**: Save and organize your learning sessions
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Dark/Light Theme**: Toggle between themes for comfortable learning

### Technical Features
- **Real-time Streaming**: Get responses as they're generated
- **Share Conversations**: Share your learning sessions with others
- **Session Persistence**: Your progress is automatically saved
- **Error Handling**: Robust error handling with graceful fallbacks

## 🛠️ Technology Stack

### Backend
- **Flask**: Python web framework
- **Supabase**: PostgreSQL database with real-time capabilities
- **Groq API**: AI-powered intent classification and response generation
- **Hugging Face**: Text embeddings for semantic search
- **Gunicorn**: Production WSGI server

### Frontend
- **HTML5/CSS3**: Modern, responsive design
- **JavaScript (ES6+)**: Interactive user interface
- **Server-Sent Events**: Real-time streaming responses

### AI/ML
- **Scikit-learn**: Cosine similarity for semantic search
- **NumPy/Pandas**: Data processing and manipulation
- **ReportLab**: PDF generation

## 📋 Prerequisites

- Python 3.8+
- Supabase account and project
- Groq API key
- Hugging Face API token
- Google OAuth credentials

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/DSA-ChatBot.git
cd DSA-ChatBot
```

### 2. Set Up Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `env.example` to `.env` and fill in your credentials:
```bash
cp env.example .env
```

Required environment variables:
```bash
# Flask Configuration
FLASK_CONFIG=development
FLASK_SECRET_KEY=your-secret-key-here

# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key

# AI/ML API Keys
GROQ_API_KEY=your-groq-api-key
HF_API_TOKEN=your-huggingface-api-token

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
REDIRECT_URI=http://localhost:5000/oauth2callback
```

### 4. Run the Application
```bash
# Development
python run.py

# Production
gunicorn wsgi:application
```

The application will be available at `http://localhost:5000`

## 🚀 Deployment

### Render Deployment
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn wsgi:application`
5. Add all environment variables from your `.env` file
6. Deploy!

### Other Platforms
The application is compatible with:
- Heroku
- Railway
- DigitalOcean App Platform
- Any platform supporting Python/Flask

## 📁 Project Structure

```
DSA-ChatBot/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration management
│   ├── extensions.py        # External service initialization
│   ├── models.py            # Database models (if needed)
│   ├── auth/                # Authentication routes
│   ├── main/                # Main application routes
│   ├── services/            # Business logic services
│   ├── static/              # CSS, JS, and static assets
│   └── templates/           # HTML templates
├── requirements.txt         # Python dependencies
├── Procfile                # Production deployment config
├── wsgi.py                 # WSGI entry point
├── run.py                  # Development entry point
└── env.example             # Environment variables template
```

## 🔧 Configuration

### Development vs Production
- **Development**: Debug mode enabled, insecure transport allowed
- **Production**: Debug disabled, secure cookies, proper logging

### Environment Variables
All configuration is handled through environment variables for security and flexibility.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Groq for AI-powered responses
- Hugging Face for embeddings
- Supabase for database and authentication
- Flask community for the excellent framework

## 📞 Support

If you encounter any issues or have questions:
1. Check the existing issues
2. Create a new issue with detailed information
3. Include error logs and environment details

---

**Happy Learning! 🎓**