"""
Connect Four Arena - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apis.api import router

app = FastAPI(
    title="Connect Four Arena",
    description="Minimax AI vs Human Connect Four game",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include game router
app.include_router(router)


@app.get("/health", summary="Health check")
def health():
    """Quick health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
