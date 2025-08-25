# UzQuiz Craft Backend

FastAPI asosida yaratilgan professional quiz tizimi backend server.

## 🚀 Texnologiyalar

- **FastAPI** - Zamonaviy Python web framework
- **JWT** - JSON Web Token autentifikatsiya
- **bcrypt** - Password hashing
- **Python-multipart** - File upload support
- **Static Files** - Rasm fayllarini ko'rsatish

## 🛠️ O'rnatish

### 1. Python Environment

```bash
# Python 3.8+ kerak
python --version

# Virtual environment yaratish
python -m venv venv

# Virtual environment ni faollashtirish
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Dependencies

```bash
# Dependencies o'rnatish
pip install -r requirements.txt
```

### 3. Environment Configuration

`.env` faylini yarating:

```env
# JWT Configuration
SECRET_KEY=your_super_secret_key_change_this_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# File Upload Configuration
MAX_FILE_SIZE=5242880
ALLOWED_IMAGE_TYPES=image/jpeg,image/png
```

## 🚀 Ishga Tushirish

### Development

```bash
# Development server
python main.py
```

### Production

```bash
# Gunicorn bilan
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Server `http://localhost:8000` da ishga tushadi.

## 📚 API Dokumentatsiya

### Swagger UI
- URL: `http://localhost:8000/docs`
- Interactive API documentation

### ReDoc
- URL: `http://localhost:8000/redoc`
- Alternative documentation format

## 🔐 API Endpoints

### Authentication

#### POST /register
Foydalanuvchi ro'yxatdan o'tish

**Request Body (FormData):**
- `username`: string (required)
- `password`: string (required)

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "username": "username"
}
```

#### POST /login
Tizimga kirish

**Request Body (FormData):**
- `username`: string (required)
- `password`: string (required)

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "username": "username"
}
```

### Groups

#### POST /groups
Yangi guruh yaratish

**Request Body (FormData):**
- `token`: string (required) - JWT token
- `title`: string (required) - Guruh nomi

**Response:**
```json
{
  "message": "Guruh muvaffaqiyatli yaratildi",
  "group_id": 1
}
```

### Questions

#### POST /questions
Yangi savol yaratish

**Request Body (FormData):**
- `token`: string (required) - JWT token
- `group_title`: string (required) - Guruh nomi
- `text`: string (required) - Savol matni
- `answer1`: string (required) - 1-javob
- `answer2`: string (required) - 2-javob
- `answer3`: string (required) - 3-javob
- `answer4`: string (required) - 4-javob
- `correct_answer`: integer (required) - To'g'ri javob indeksi (1-4)
- `image`: file (optional) - Rasm fayli

**Response:**
```json
{
  "message": "Savol muvaffaqiyatli yaratildi",
  "question_id": 1
}
```

#### GET /questions/all
Barcha savollarni olish

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "created_by": "username",
  "quations": [
    {
      "id": 1,
      "title": "Guruh nomi",
      "quations": [
        {
          "id": 1,
          "text": "Savol matni",
          "answers": [
            {"text": "Javob 1", "is_correct": true},
            {"text": "Javob 2", "is_correct": false}
          ],
          "image": "uploads/filename.jpg",
          "created_at": "2024-01-01T00:00:00"
        }
      ]
    }
  ]
}
```

#### GET /questions/test
Test uchun savollarni olish

**Query Parameters:**
- `token`: string (required) - JWT token
- `group_title`: string (required) - Guruh nomi
- `shuffle_questions`: boolean (optional) - Savollarni aralashtirish (default: true)
- `shuffle_answers`: boolean (optional) - Javoblarni aralashtirish (default: true)

**Response:**
```json
{
  "message": "Test muvaffaqiyatli yuklandi",
  "group_title": "Guruh nomi",
  "total_questions": 5,
  "shuffle_questions": true,
  "shuffle_answers": true,
  "questions": [...]
}
```

### Users

#### GET /users
Barcha foydalanuvchilarni olish

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
[
  {"username": "user1"},
  {"username": "user2"}
]
```

#### DELETE /users/{username}
Foydalanuvchini o'chirish

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Foydalanuvchi o'chirildi"
}
```

#### DELETE /users
Barcha foydalanuvchilarni o'chirish

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Barcha foydalanuvchilar o'chirildi"
}
```

## 🔒 Xavfsizlik

### JWT Authentication
- Token muddati: 60 daqiqa (configurable)
- Algorithm: HS256
- Secret key environment variable dan olinadi

### Password Security
- bcrypt bilan hashlangan
- Salt avtomatik qo'shiladi

### CORS Protection
- Frontend origin lar ro'yxatda
- Credentials ruxsat etilgan

### File Upload Security
- Rasm formatlari: JPEG, PNG
- Maksimal hajm: 5MB (configurable)
- Unique filename generation

## 📁 Fayl Strukturasi

```
chek_test/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── .env                # Environment variables
├── users.json          # Foydalanuvchilar ma'lumotlari
├── data.json           # Quiz ma'lumotlari
├── uploads/            # Rasm fayllari
└── README.md           # Bu fayl
```

## 🐛 Xatoliklar

### Umumiy Xatoliklar

- `400 Bad Request`: Noto'g'ri request data
- `401 Unauthorized`: Token yo'q yoki noto'g'ri
- `404 Not Found`: Ma'lumot topilmadi
- `500 Internal Server Error`: Server xatoligi

### Xatolik Response Format

```json
{
  "detail": "Xatolik xabari"
}
```

## 🚀 Production Deployment

### Environment Variables
```env
SECRET_KEY=production_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=60
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=https://yourdomain.com
MAX_FILE_SIZE=5242880
ALLOWED_IMAGE_TYPES=image/jpeg,image/png
```

### Gunicorn Configuration
```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 2
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads/ {
        alias /path/to/chek_test/uploads/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log
```

## 🤝 Contributing

1. Fork qiling
2. Feature branch yarating
3. O'zgarishlarni commit qiling
4. Pull request yarating

## 📄 License

MIT License

---

**UzQuiz Craft Backend** - Professional quiz tizimi backend server! 🚀
