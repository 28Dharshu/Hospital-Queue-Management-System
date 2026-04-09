from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import datetime
from database import users_collection, queue_collection

app = FastAPI()

# CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add your API key here 👇
client = Groq(api_key="YOUR GROQ API KEY")

class AuthData(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(data: AuthData):
    if users_collection.find_one({"username": data.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    # Store plain password for simplicity, but in prod should be hashed
    users_collection.insert_one({"username": data.username, "password": data.password})
    return {"message": "Success"}

@app.post("/login")
def login(data: AuthData):
    user = users_collection.find_one({"username": data.username, "password": data.password})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return {"message": "Logged in"}

@app.get("/")
def home():
    return {"message": "Groq AI Running"}

@app.post("/chat")
def chat(data: dict):
    user_input = data["message"]
    username = data.get("username", "guest")

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a hospital assistant. Analyze symptoms and give severity (low, medium, high) and estimated waiting time. Output strictly as JSON with keys 'severity' and 'waiting_time'."},
            {"role": "user", "content": user_input}
        ]
    )

    import json
    try:
        reply = json.loads(response.choices[0].message.content)
    except:
        reply = {"severity": "low", "waiting_time": 0}

    # Store in queue
    queue_collection.insert_one({
        "username": username,
        "symptoms": user_input,
        "severity": reply.get("severity", "low").lower(),
        "waiting_time": reply.get("waiting_time", 0),
        "timestamp": datetime.datetime.utcnow()
    })

    return reply

@app.get("/queue")
def get_queue():
    # Fetch all waiting tickets
    tickets = list(queue_collection.find({}, {"_id": 0}))
    
    # Sort tickets: High first, then Medium, then Low, and then by arrival time
    severity_order = {"high": 1, "medium": 2, "low": 3}
    
    tickets.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["timestamp"]))
    
    return tickets