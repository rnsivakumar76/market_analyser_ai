from fastapi import FastAPI
from mangum import Mangum
from datetime import datetime

app = FastAPI()

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

handler = Mangum(app)
