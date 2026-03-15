"""
Wundio – /api/users routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_engine, log_event
from database import User

router = APIRouter(tags=["users"])


class UserCreate(BaseModel):
    name: str
    display_name: str
    avatar_emoji: str = "🎵"
    volume: int = 70


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_emoji: Optional[str] = None
    volume: Optional[int] = None
    spotify_playlist_id: Optional[str] = None
    spotify_playlist_name: Optional[str] = None


@router.get("/", response_model=List[User])
async def list_users():
    with Session(get_engine()) as session:
        return session.exec(select(User).where(User.is_active == True)).all()


@router.post("/", response_model=User)
async def create_user(data: UserCreate):
    with Session(get_engine()) as session:
        user = User(**data.model_dump())
        session.add(user)
        session.commit()
        session.refresh(user)
        log_event("users", f"User created: {user.name}")
        return user


@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: int, data: UserUpdate):
    with Session(get_engine()) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@router.delete("/{user_id}")
async def delete_user(user_id: int):
    with Session(get_engine()) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = False
        session.add(user)
        session.commit()
        log_event("users", f"User deactivated: {user.name}")
        return {"ok": True}
