from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InteractionCreate
from app import crud

router = APIRouter(
    prefix="/interaction",
    tags=["Interaction"]
)

@router.post("/")
def create_interaction(data: InteractionCreate, db: Session = Depends(get_db)):
    return crud.create_interaction(db, data)



@router.put("/{id}")
def update_interaction(id: int, data: InteractionCreate, db: Session = Depends(get_db)):
    return crud.update_interaction(db, id, data)