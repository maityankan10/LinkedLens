from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register")
def register_user():
    return {"message": "User registration endpoint"}
