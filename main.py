from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import random
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import shutil

# -------------------------------------------------
# App meta
# -------------------------------------------------
app = FastAPI(
    title="TEST (Multi-user + JWT + Questions)", 
    version="2.0.0",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Foydalanuvchi ro'yxatdan o'tish va login qilish"
        },
        {
            "name": "Questions",
            "description": "Savollar bilan ishlash: kiritish va olish"
        }
    ]
)

# -------------------------------------------------
# Storage & constants
# -------------------------------------------------
USERS_FILE = "users.json"
DATA_FILE = "data.json"
UPLOADS_DIR = "uploads"

# JWT settings
SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"  # Real loyihada .env dan oling!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 (Swagger uchun tokenUrl = /login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Uploads papkasini yaratish
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# -------------------------------------------------
# Pydantic models
# -------------------------------------------------
class UserPublic(BaseModel):
    username: str

class AnswerOption(BaseModel):
    text: str
    is_correct: bool

class QuestionCreate(BaseModel):
    text: str
    answers: List[AnswerOption]
    image: Optional[str] = None

class QuestionPublic(BaseModel):
    id: int
    text: str
    answers: List[str]
    image: Optional[str] = None
    created_by: str
    created_at: str

# -------------------------------------------------
# File helpers
# -------------------------------------------------
def safe_load_json(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        return []

def save_json(filepath: str, data: list):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users() -> list:
    return safe_load_json(USERS_FILE)

def save_users(users: list) -> None:
    save_json(USERS_FILE, users)

def load_data() -> list:
    return safe_load_json(DATA_FILE)

def save_data(data: list) -> None:
    save_json(DATA_FILE, data)

def get_user_by_token(token: str):
    """Token bo'yicha foydalanuvchini topish"""
    users = load_users()
    for user_data in users:
        if user_data.get("token") == token:
            return user_data
    return None

def get_user_questions(user_id: int):
    """Foydalanuvchining savollarini olish"""
    data = load_data()
    for user_data in data:
        if user_data.get("user_id") == user_id:
            return user_data.get("quations", [])
    return []

# -------------------------------------------------
# Auth helpers
# -------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_current_user(token: str) -> dict:
    user_data = get_user_by_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Token noto'g'ri yoki muddati tugagan")
    return user_data

# -------------------------------------------------
# Auth endpoints
# -------------------------------------------------
@app.post("/register", tags=["Authentication"])
def register(username: str = Form(...), password: str = Form(...)):
    users = load_users()
    if any(u.get("user") == username for u in users):
        raise HTTPException(status_code=400, detail="Bunday foydalanuvchi allaqachon mavjud")

    # Yangi foydalanuvchi yaratish
    hashed_password = hash_password(password)
    token = create_access_token({"sub": username})
    
    new_user = {
        "id": len(users) + 1,
        "user": username,
        "hashed_password": hashed_password,
        "token": token,
        "created_at": datetime.now().isoformat()
    }
    
    users.append(new_user)
    save_users(users)
    return {"access_token": token, "token_type": "bearer", "username": username}

@app.post("/login", tags=["Authentication"])
def login(username: str = Form(...), password: str = Form(...)):
    users = load_users()
    user = next((u for u in users if u.get("user") == username), None)
    if not user or not verify_password(password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    
    # Yangi token yaratish va saqlash
    token = create_access_token({"sub": user["user"]})
    user["token"] = token
    save_users(users)
    
    return {"access_token": token, "token_type": "bearer", "username": user["user"]}

# -------------------------------------------------
# User management
# -------------------------------------------------
@app.get("/users", response_model=list[UserPublic], tags=["Authentication"])
def get_all_users(current_user: dict = Depends(get_current_user)):
    users = load_users()
    return [{"username": u.get("user", "")} for u in users]

@app.delete("/users/{username}", tags=["Authentication"])
def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    users = load_users()
    user = next((u for u in users if u.get("user") == username), None)
    if not user:
        raise HTTPException(status_code=404, detail="Bunday foydalanuvchi topilmadi")
    if username != current_user.get("user", ""):
        raise HTTPException(status_code=403, detail="Faqat o'z akkauntingizni o'chirishingiz mumkin")

    # Foydalanuvchining savollarini ham o'chirish
    data = load_data()
    data = [q for q in data if q.get("user_id") != user.get("id")]
    save_data(data)

    users = [u for u in users if u.get("user") != username]
    save_users(users)
    return {"message": f"{username} foydalanuvchisi o'chirildi"}

@app.delete("/users", tags=["Authentication"])
def delete_all_users(current_user: dict = Depends(get_current_user)):
    save_users([])
    save_data([])
    return {"message": "Barcha foydalanuvchilar va savollar o'chirildi!"}

# -------------------------------------------------
# Questions endpoints
# -------------------------------------------------
@app.post("/groups", tags=["Questions"])
def create_group(
    token: str = Form(...),
    title: str = Form(...)
):
    """Yangi guruh yaratish (masalan: Matematika, Fizika)"""
    # Tokenni tekshirish
    current_user = get_current_user(token)
    
    # data.json ni yuklash
    data = load_data()
    
    # Foydalanuvchining mavjud ma'lumotlarini topish
    user_data = next((ud for ud in data if ud.get("user_id") == current_user.get("id")), None)
    
    if user_data:
        # Mavjud foydalanuvchiga guruh qo'shish
        # Guruh nomi allaqachon mavjudligini tekshirish
        existing_group = next((g for g in user_data.get("quations", []) if g.get("title") == title), None)
        if existing_group:
            raise HTTPException(status_code=400, detail=f"'{title}' nomli guruh allaqachon mavjud")
        
        # Yangi guruh yaratish
        new_group = {
            "id": len(user_data["quations"]) + 1,
            "title": title,
            "quations": []
        }
        user_data["quations"].append(new_group)
        group_id = new_group["id"]
    else:
        # Yangi foydalanuvchi uchun guruh yaratish
        new_user_data = {
            "id": len(data) + 1,
            "user_id": current_user.get("id"),
            "created_by": current_user.get("user", ""),
            "quations": [
                {
                    "id": 1,
                    "title": title,
                    "quations": []
                }
            ]
        }
        data.append(new_user_data)
        group_id = 1
    
    save_data(data)
    return {"message": f"'{title}' guruhi muvaffaqiyatli yaratildi", "group_id": group_id}

@app.post("/questions", tags=["Questions"])
def create_question(
    token: str = Form(...),
    group_title: str = Form(...),  # Qaysi guruhga qo'shilishini belgilash
    text: str = Form(...),
    answer1: str = Form(...),
    answer2: str = Form(...),
    answer3: str = Form(...),
    answer4: str = Form(...),
    correct_answer: int = Form(..., ge=1, le=4),
    image: Optional[UploadFile] = File(None)  # Rasm ixtiyoriy
):
    # Tokenni tekshirish
    current_user = get_current_user(token)
    
    # Javoblar ro'yxati
    answers = [
        {"text": answer1, "is_correct": correct_answer == 1},
        {"text": answer2, "is_correct": correct_answer == 2},
        {"text": answer3, "is_correct": correct_answer == 3},
        {"text": answer4, "is_correct": correct_answer == 4}
    ]
    
    # Rasmni saqlash (agar rasm kiritilgan bo'lsa)
    image_path = None
    if image and hasattr(image, 'filename') and image.filename and image.size > 0:
        if image.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Faqat JPEG yoki PNG rasmlar ruxsat etilgan")
        if image.size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Rasm hajmi 5MB dan oshmasligi kerak")
        
        image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"
        image_path = os.path.join(UPLOADS_DIR, image_filename)
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    
    # Savolni yaratish
    question = {
        "id": 1,  # Har bir guruhda alohida ID
        "text": text,
        "answers": answers,
        "image": image_path,
        "created_at": datetime.now().isoformat()
    }
    
    # Savolni data.json ga qo'shish
    data = load_data()
    
    # Foydalanuvchining mavjud ma'lumotlarini topish
    user_data = next((ud for ud in data if ud.get("user_id") == current_user.get("id")), None)
    
    if user_data:
        # Berilgan guruhni topish
        target_group = next((g for g in user_data.get("quations", []) if g.get("title") == group_title), None)
        if not target_group:
            raise HTTPException(status_code=404, detail=f"'{group_title}' nomli guruh topilmadi. Avval guruh yarating!")
        
        # Guruhga savol qo'shish
        question["id"] = len(target_group["quations"]) + 1
        target_group["quations"].append(question)
    else:
        # Yangi foydalanuvchi uchun avtomatik "Umumiy" guruh yaratish
        new_user_data = {
            "id": len(data) + 1,
            "user_id": current_user.get("id"),
            "created_by": current_user.get("user", ""),
            "quations": [
                {
                    "id": 1,
                    "title": "Umumiy",
                    "quations": [question]
                }
            ]
        }
        data.append(new_user_data)
    
    save_data(data)
    return {"message": f"Savol '{group_title}' guruhiga muvaffaqiyatli qo'shildi", "question_id": question["id"]}

@app.get("/questions/all", tags=["Questions"])
def get_all_user_questions(current_user: dict = Depends(get_current_user)):
    """Foydalanuvchi o'zi yaratgan barcha savollarni olish"""
    data = load_data()
    
    # Faqat o'zi yaratgan savollarni olish
    user_data = next((ud for ud in data if ud.get("user_id") == current_user.get("id")), None)
    
    if not user_data:
        return []
    
    return user_data

@app.get("/questions/test", tags=["Questions"])
def get_test_questions(
    token: str = Query(...),
    group_title: str = Query(..., description="Qaysi guruhdan savollar olinadi (masalan: Matematika, Fizika)"),
    shuffle_questions: bool = Query(True, description="Savollarni aralashtirish"),
    shuffle_answers: bool = Query(True, description="Javoblarni aralashtirish")
):
    """Ma'lum bir guruhdan test savollarini aralashtirib berish"""
    # Tokenni tekshirish
    current_user = get_current_user(token)
    
    # data.json ni yuklash
    data = load_data()
    
    # Foydalanuvchining mavjud ma'lumotlarini topish
    user_data = next((ud for ud in data if ud.get("user_id") == current_user.get("id")), None)
    
    if not user_data:
        return {"message": "Foydalanuvchi topilmadi", "questions": []}
    
    # Berilgan guruhni topish
    target_group = next((g for g in user_data.get("quations", []) if g.get("title") == group_title), None)
    
    if not target_group:
        available_groups = [g.get("title") for g in user_data.get("quations", [])]
        return {
            "message": f"'{group_title}' nomli guruh topilmadi",
            "available_groups": available_groups,
            "questions": []
        }
    
    # Faqat shu guruhning savollarini olish
    group_questions = []
    for question in target_group.get("quations", []):
        # Savol ma'lumotlarini nusxalash
        question_copy = {
            "id": question.get("id"),
            "group_title": group_title,
            "text": question.get("text"),
            "answers": question.get("answers", []).copy(),  # Javoblarni nusxalash
            "image": question.get("image"),
            "created_at": question.get("created_at")
        }
        group_questions.append(question_copy)
    
    if not group_questions:
        return {
            "message": f"'{group_title}' guruhida savollar topilmadi",
            "total_questions": 0,
            "questions": []
        }
    
    # 1. Savollarni aralashtirish
    if shuffle_questions:
        random.shuffle(group_questions)
    
    # 2. Har bir savolning javoblarini aralashtirish
    if shuffle_answers:
        for question in group_questions:
            random.shuffle(question["answers"])
    
    return {
        "message": f"'{group_title}' guruhidan {len(group_questions)} ta savol aralashtirildi",
        "group_title": group_title,
        "total_questions": len(group_questions),
        "shuffle_questions": shuffle_questions,
        "shuffle_answers": shuffle_answers,
        "questions": group_questions
    }

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
