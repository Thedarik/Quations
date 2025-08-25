# Questions API - FastAPI

Bu loyiha foydalanuvchilarga savollar yaratish, guruhlash va test qilish imkonini beradi.

## 🚀 Xususiyatlar

- **JWT Authentication** - Xavfsiz foydalanuvchi autentifikatsiyasi
- **Guruhlar** - Savollarni mavzular bo'yicha guruhlash (Matematika, Fizika h.k.)
- **Test savollari** - Savollarni aralashtirib test qilish
- **Rasm qo'shish** - Savollarga rasm qo'shish (ixtiyoriy)
- **Multi-user** - Har bir foydalanuvchi faqat o'zi yaratgan savollarni ko'radi

## 📋 API Endpointlar

### Authentication
- `POST /register` - Ro'yxatdan o'tish
- `POST /login` - Kirish

### User Management
- `GET /users` - Barcha foydalanuvchilarni ko'rish
- `DELETE /users/{username}` - Foydalanuvchini o'chirish
- `DELETE /users` - Barcha foydalanuvchilarni o'chirish

### Questions
- `POST /groups` - Yangi guruh yaratish
- `POST /questions` - Savol qo'shish
- `GET /questions/all` - Barcha savollarni ko'rish
- `GET /questions/test` - Test savollarini aralashtirib olish

## 🛠️ O'rnatish

### 1. Repository ni klonlash
```bash
git clone https://github.com/Thedarik/Quations.git
cd Quations
```

### 2. Virtual environment yaratish
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# yoki
venv\Scripts\activate  # Windows
```

### 3. Kerakli paketlarni o'rnatish
```bash
pip install fastapi uvicorn python-multipart python-jose[cryptography] passlib[bcrypt]
```

### 4. Dasturni ishga tushirish
```bash
uvicorn main:app --reload
```

Dastur `http://localhost:8000` da ishga tushadi.

## 📖 Foydalanish

### 1. Ro'yxatdan o'tish
```bash
POST /register
Form data:
- username: "Samandar"
- password: "123456"
```

### 2. Kirish
```bash
POST /login
Form data:
- username: "Samandar"
- password: "123456"
```

### 3. Guruh yaratish
```bash
POST /groups
Form data:
- token: "your_jwt_token"
- title: "Matematika"
```

### 4. Savol qo'shish
```bash
POST /questions
Form data:
- token: "your_jwt_token"
- group_title: "Matematika"
- text: "2+2=?"
- answer1: "4"
- answer2: "5"
- answer3: "6"
- answer4: "7"
- correct_answer: 1
- image: [optional file]
```

### 5. Test savollarini olish
```bash
GET /questions/test?token=your_token&group_title=Matematika&shuffle_questions=true&shuffle_answers=true
```

## 📁 Fayl struktura

```
Quations/
├── main.py          # Asosiy FastAPI dasturi
├── users.json       # Foydalanuvchilar ma'lumotlari
├── data.json        # Savollar ma'lumotlari
├── uploads/         # Rasm fayllari
├── venv/            # Virtual environment
└── README.md        # Bu fayl
```

## 🔐 Xavfsizlik

- JWT tokenlar 60 daqiqa muddatga ega
- Parollar bcrypt orqali hash qilinadi
- Har bir foydalanuvchi faqat o'zi yaratgan ma'lumotlarni ko'radi

## 🌐 Swagger UI

Dastur ishga tushgandan so'ng `http://localhost:8000/docs` da Swagger UI orqali API ni sinab ko'rishingiz mumkin.

## 📝 Misol

### data.json struktura
```json
[
  {
    "id": 1,
    "user_id": 1,
    "created_by": "Samandar",
    "quations": [
      {
        "id": 1,
        "title": "Matematika",
        "quations": [
          {
            "id": 1,
            "text": "2+2=?",
            "answers": [
              {"text": "4", "is_correct": true},
              {"text": "5", "is_correct": false},
              {"text": "6", "is_correct": false},
              {"text": "7", "is_correct": false}
            ],
            "image": null,
            "created_at": "2025-01-27T12:00:00"
          }
        ]
      }
    ]
  }
]
```

## 🤝 Hissa qo'shish

1. Repository ni fork qiling
2. Yangi branch yarating (`git checkout -b feature/yangi-xususiyat`)
3. O'zgarishlarni commit qiling (`git commit -am 'Yangi xususiyat qo'shildi'`)
4. Branch ni push qiling (`git push origin feature/yangi-xususiyat`)
5. Pull Request yarating

## 📞 Aloqa

- GitHub: [@Thedarik](https://github.com/Thedarik)
- Repository: [Quations](https://github.com/Thedarik/Quations.git)

## 📄 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.
