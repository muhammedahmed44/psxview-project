"""Authenticated academy progress and contextual tutoring."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from auth import get_current_user
from db import get_db
from models import AcademyProgress, User
import ai

router = APIRouter(prefix='/api/academy', tags=['academy'])
class ProgressIn(BaseModel):
    module_id: str = Field(min_length=1, max_length=40)
    progress: float = Field(ge=0, le=100)
    score: int = Field(ge=0, le=20)
class ExplainIn(BaseModel):
    lesson: str
    content: str
    language: str = 'English'
    mode: str = 'beginner'

@router.get('/progress')
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{'module_id':x.module_id,'progress':x.progress,'score':x.score} for x in db.scalars(select(AcademyProgress).where(AcademyProgress.user_id==user.id)).all()]
@router.post('/progress')
def save(body: ProgressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row=db.scalar(select(AcademyProgress).where(AcademyProgress.user_id==user.id, AcademyProgress.module_id==body.module_id))
    if not row: row=AcademyProgress(user_id=user.id,module_id=body.module_id); db.add(row)
    row.progress=max(row.progress or 0, body.progress); row.score=max(row.score or 0, body.score); db.commit(); return {'ok':True}
@router.post('/explain')
def explain(body: ExplainIn, user: User | None = Depends(lambda: None)):
    # Teaching uses the existing provider; no market facts are added to the prompt.
    prompt=f"Explain this lesson in {body.language}, {body.mode} mode. Lesson: {body.lesson}. Content: {body.content}. Be concise, factual, and say educational only."
    result=ai.explain({'symbol':'academy','eps':1,'price':1,'years':1,'growth_pct':0,'terminal_pct':0},{'required_return_pct':0,'implied_growth_pct':0,'fair_value':1,'upside_pct':0})
    return {'text':result['text'],'source':result['source']}
