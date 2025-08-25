from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File, Query, Header
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import random
import logging
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO

# -------------------------------------------------
# App meta
# -------------------------------------------------
app = FastAPI(
    title="UzQuiz Craft - Professional Quiz Platform", 
    version="3.0.0",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Foydalanuvchi ro'yxatdan o'tish va login qilish"
        },
        {
            "name": "Questions",
            "description": "Savollar bilan ishlash: kiritish va olish"
        },
        {
            "name": "System",
            "description": "Tizim holati va monitoring"
        }
    ]
)

# CORS middleware qo'shish - TEST UCHUN BARCHA DOMENLARNI RUXSAT BERISH
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Test uchun barcha domenlar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Storage & constants
# -------------------------------------------------
USERS_FILE = "users.json"
DATA_FILE = "data.json"
UPLOADS_DIR = "uploads"

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_CHANGE_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 (Swagger uchun tokenUrl = /login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Uploads papkasini yaratish
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# Static files uchun uploads papkasini mount qilish
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Noto'g'ri ma'lumotlar kiritildi", "errors": str(exc)}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Server xatoligi yuz berdi", "error": str(exc)}
    )

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
        logger.error(f"JSON decode error for file: {filepath}")
        return []

def save_json(filepath: str, data: list):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving JSON file {filepath}: {e}")
        raise

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

def get_current_user_by_token(token: str) -> dict:
    """Token orqali foydalanuvchini olish"""
    user_data = get_user_by_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Token noto'g'ri yoki muddati tugagan")
    return user_data

def get_current_user_by_header(authorization: str = Header(None)) -> dict:
    """Authorization header orqali foydalanuvchini olish"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header kerak")
    
    token = authorization.split(" ")[1]
    return get_current_user_by_token(token)

# -------------------------------------------------
# Health check
# -------------------------------------------------
@app.get("/", tags=["System"])
def root():
    """Root endpoint"""
    return {
        "message": "UzQuiz Craft API ishlamoqda!",
        "version": "3.0.0",
        "status": "active"
    }

@app.get("/health", tags=["System"])
def health_check():
    """Server holatini tekshirish"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "users_count": len(load_users()),
        "questions_count": len(load_data())
    }

# -------------------------------------------------
# Auth endpoints - TUZATILGAN!
# -------------------------------------------------
@app.post("/register", tags=["Authentication"])
def register(username: str = Form(...), password: str = Form(...)):
    """Foydalanuvchi ro'yxatdan o'tkazish"""
    logger.info(f"Registration attempt for username: {username}")
    
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username kamida 3 belgi bo'lishi kerak")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Parol kamida 6 belgi bo'lishi kerak")
    
    users = load_users()
    if any(u.get("user") == username for u in users):
        logger.warning(f"Registration failed: username {username} already exists")
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
    logger.info(f"User {username} successfully registered")
    return {"access_token": token, "token_type": "bearer", "username": username}

@app.post("/login", tags=["Authentication"])
def login(username: str = Form(...), password: str = Form(...)):
    """Tizimga kirish"""
    logger.info(f"Login attempt for username: {username}")
    
    users = load_users()
    user = next((u for u in users if u.get("user") == username), None)
    if not user or not verify_password(password, user.get("hashed_password", "")):
        logger.warning(f"Login failed for username: {username} - invalid credentials")
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    
    # Yangi token yaratish va saqlash
    token = create_access_token({"sub": user["user"]})
    user["token"] = token
    save_users(users)
    
    logger.info(f"User {username} successfully logged in")
    return {"access_token": token, "token_type": "bearer", "username": user["user"]}

# -------------------------------------------------
# User management
# -------------------------------------------------
@app.get("/users", response_model=List[UserPublic], tags=["Authentication"])
def get_all_users(current_user: dict = Depends(get_current_user_by_header)):
    """Barcha foydalanuvchilarni olish"""
    users = load_users()
    return [{"username": u.get("user", "")} for u in users]

@app.delete("/users/{username}", tags=["Authentication"])
def delete_user(username: str, current_user: dict = Depends(get_current_user_by_header)):
    """Foydalanuvchini o'chirish"""
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
def delete_all_users(current_user: dict = Depends(get_current_user_by_header)):
    """Barcha foydalanuvchilarni o'chirish"""
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
    logger.info(f"Creating group: {title}")
    
    # Tokenni tekshirish
    current_user = get_current_user_by_token(token)
    
    if len(title.strip()) < 2:
        raise HTTPException(status_code=400, detail="Guruh nomi kamida 2 belgi bo'lishi kerak")
    
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
    logger.info(f"Group '{title}' created successfully by {current_user.get('user')}")
    return {"message": f"'{title}' guruhi muvaffaqiyatli yaratildi", "group_id": group_id}

@app.post("/questions", tags=["Questions"])
def create_question(
    token: str = Form(...),
    group_title: str = Form(...),
    text: str = Form(...),
    answer1: str = Form(...),
    answer2: str = Form(...),
    answer3: str = Form(...),
    answer4: str = Form(...),
    correct_answer: int = Form(..., ge=1, le=4),
    image: Optional[UploadFile] = File(None)
):
    """Yangi savol yaratish"""
    logger.info(f"Creating question for group: {group_title}")
    
    # Tokenni tekshirish
    current_user = get_current_user_by_token(token)
    
    # Validation
    if len(text.strip()) < 5:
        raise HTTPException(status_code=400, detail="Savol matni kamida 5 belgi bo'lishi kerak")
    
    for i, answer in enumerate([answer1, answer2, answer3, answer4], 1):
        if len(answer.strip()) < 1:
            raise HTTPException(status_code=400, detail=f"{i}-javob bo'sh bo'lmasligi kerak")
    
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
        # File type validation
        allowed_types = ["image/jpeg", "image/png", "image/jpg"]
        if image.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Faqat JPG, PNG formatlar ruxsat etilgan")
        
        # File size validation (5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if image.size > max_size:
            raise HTTPException(status_code=400, detail=f"Rasm hajmi 5MB dan oshmasligi kerak")
        
        # Generate unique filename
        image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"
        image_path = os.path.join(UPLOADS_DIR, image_filename)
        
        # Save file
        try:
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise HTTPException(status_code=500, detail="Rasmni saqlashda xatolik")
    
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
                    "title": group_title,
                    "quations": [question]
                }
            ]
        }
        data.append(new_user_data)
    
    save_data(data)
    logger.info(f"Question created successfully in group '{group_title}' by {current_user.get('user')}")
    return {"message": f"Savol '{group_title}' guruhiga muvaffaqiyatli qo'shildi", "question_id": question["id"]}

@app.get("/questions/all", tags=["Questions"])
def get_all_user_questions(current_user: dict = Depends(get_current_user_by_header)):
    """Foydalanuvchi o'zi yaratgan barcha savollarni olish"""
    logger.info(f"Getting all questions for user: {current_user.get('user')}")
    
    data = load_data()
    
    # Faqat o'zi yaratgan savollarni olish
    user_data = next((ud for ud in data if ud.get("user_id") == current_user.get("id")), None)
    
    if not user_data:
        return {"quations": []}
    
    return user_data

@app.get("/questions/test", tags=["Questions"])
def get_test_questions(
    token: str = Query(...),
    group_title: str = Query(..., description="Qaysi guruhdan savollar olinadi"),
    shuffle_questions: bool = Query(True, description="Savollarni aralashtirish"),
    shuffle_answers: bool = Query(True, description="Javoblarni aralashtirish")
):
    """Ma'lum bir guruhdan test savollarini aralashtirib berish"""
    logger.info(f"Getting test questions for group: {group_title}")
    
    # Tokenni tekshirish
    current_user = get_current_user_by_token(token)
    
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
            "answers": question.get("answers", []).copy(),
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
    
    logger.info(f"Returning {len(group_questions)} questions for group '{group_title}'")
    return {
        "message": f"'{group_title}' guruhidan {len(group_questions)} ta savol aralashtirildi",
        "group_title": group_title,
        "total_questions": len(group_questions),
        "shuffle_questions": shuffle_questions,
        "shuffle_answers": shuffle_answers,
        "questions": group_questions
    }

@app.get("/questions/pdf", tags=["Questions"])
def get_questions_pdf(
    token: str = Query(...),
    group_title: str = Query(...),
):
    """Berilgan guruh savollarini A4 formatdagi PDF fayl sifatida qaytarish"""
    logger.info(f"Generating PDF for group: {group_title}")
    
    # Tokenni tekshirish va foydalanuvchini olish
    current_user = get_current_user_by_token(token)
    
    # Guruh savollarini olish (avvalgi logikaga o'xshash)
    data = load_data()
    user_data = next((ud for ud in data if ud.get("user_id") == current_user.get("id")), None)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="Foydalanuvchi ma'lumotlari topilmadi")
    
    target_group = next((g for g in user_data.get("quations", []) if g.get("title") == group_title), None)
    
    if not target_group:
        raise HTTPException(status_code=404, detail=f"'{group_title}' nomli guruh topilmadi")
    
    questions = target_group.get("quations", [])
    
    if not questions:
        raise HTTPException(status_code=404, detail=f"'{group_title}' guruhida savollar topilmadi")
    
    # PDF generatsiya
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Font sozlamalari (chiroyli ko'rinish uchun)
    c.setFont("Helvetica-Bold", 14)  # Savol uchun qalin font
    y = height - 50  # Tepadan boshlash (margins)
    
    for idx, q in enumerate(questions, 1):
        # Savol matni (bold)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"{idx}. {q['text']}")
        y -= 30  # Bo'sh joy
        
        # Rasm bo'lsa, qo'shish
        if q.get('image'):
            try:
                img = ImageReader(q['image'])
                img_width, img_height = img.getSize()
                aspect = img_height / float(img_width)
                draw_width = width - 100  # Sahifa kengligiga moslash
                draw_height = draw_width * aspect
                if draw_height > 200:  # Maksimal balandlik cheklovi
                    draw_height = 200
                    draw_width = draw_height / aspect
                c.drawImage(img, 50, y - draw_height, width=draw_width, height=draw_height)
                y -= draw_height + 20
            except Exception as e:
                logger.error(f"Rasm yuklashda xato: {e}")
                c.setFont("Helvetica", 10)
                c.drawString(50, y, "[Rasm yuklanmadi]")
                y -= 20
        
        # Javob variantlari (oddiy font)
        c.setFont("Helvetica", 12)
        for ans_idx, ans in enumerate(q['answers'], 1):
            c.drawString(70, y, f"{chr(64 + ans_idx)}. {ans['text']}")  # A., B., C., D. formatida
            y -= 20
        
        y -= 40  # Savollar orasida bo'sh joy
        
        # Agar sahifa pastki qismiga yetib qolsa, yangi sahifa
        if y < 100:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 14)
    
    c.save()
    buffer.seek(0)
    
    # PDF ni response sifatida qaytarish
    headers = {
        "Content-Disposition": f"attachment; filename={group_title}_questions.pdf"
    }
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"""
🚀 UzQuiz Craft Backend ishga tushmoqda...
📍 Server: http://{host}:{port}
📋 API Docs: http://{host}:{port}/docs
🔍 Health Check: http://{host}:{port}/health
    """)
    
    uvicorn.run(app, host=host, port=port)