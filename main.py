from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import models
from models import Transaction, User
from typing import Annotated, Optional
from database import engine, SessionLocal
from fastapi.responses import JSONResponse
from router import auth
from router.auth import get_current_user
from datetime import date

app = FastAPI()

class TransactionCreate(BaseModel):
    title: str
    amount: float = Field(gt=0, description="Amount must be positive")
    type: str = Field(pattern="^(income|expense)$", description="Type must be income or expense")
    category: str
    date: date


class TransactionUpdate(BaseModel):
    title: Optional[str] = Field(default=None)
    amount: Optional[float] = Field(default=None, gt=0)
    type: Optional[str] = Field(default=None, pattern="^(income|expense)$")
    category: Optional[str] = Field(default=None)
    date: Optional[date] = None

models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@app.post('/transactions', status_code=201)
def create_transaction(user: user_dependency, db: db_dependency, transaction: TransactionCreate):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    transaction_model = Transaction(**transaction.model_dump(), owner_id=user.get('id'))
    db.add(transaction_model)
    db.commit()
    db.refresh(transaction_model)
    return transaction_model


@app.get('/transactions')
def read_all_transactions(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    return db.query(Transaction).filter(Transaction.owner_id == user.get('id')).all()


@app.get('/transactions/filter')
def filter_transactions(
    user: user_dependency, 
    db: db_dependency,
    type: Optional[str] = Query(None, pattern="^(income|expense)$"),
    category: Optional[str] = None,
    minimum_amount: Optional[float] = Query(None, ge=0),
    maximum_amount: Optional[float] = Query(None, ge=0)
):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    query = db.query(Transaction).filter(Transaction.owner_id == user.get('id'))
    
    if type:
        query = query.filter(Transaction.type == type)
    if category:
        query = query.filter(Transaction.category == category)
    if minimum_amount is not None:
        query = query.filter(Transaction.amount >= minimum_amount)
    if maximum_amount is not None:
        query = query.filter(Transaction.amount <= maximum_amount)
        
    return query.all()

@app.get('/transactions/{transaction_id}')
def read_transaction(user: user_dependency, db: db_dependency, transaction_id: int):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    transaction = db.query(Transaction).filter(
        Transaction.owner_id == user.get('id'),
        Transaction.id == transaction_id
    ).first()
    
    if transaction is not None:
        return transaction
    raise HTTPException(status_code=404, detail='Transaction not found')


@app.put('/transactions/{transaction_id}')
def update_transaction(
    user: user_dependency, 
    db: db_dependency, 
    transaction_id: int, 
    update_data: TransactionUpdate
):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    transaction = db.query(Transaction).filter(
        Transaction.owner_id == user.get('id'),
        Transaction.id == transaction_id
    ).first()
    
    if transaction is None:
        raise HTTPException(status_code=404, detail='Transaction not found')
    
    data_dict = update_data.model_dump(exclude_unset=True)
    for key, value in data_dict.items():
        setattr(transaction, key, value)
        
    db.commit()
    db.refresh(transaction)
    return transaction


@app.delete('/transactions/{transaction_id}')
def delete_transaction(user: user_dependency, db: db_dependency, transaction_id: int):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    transaction = db.query(Transaction).filter(
        Transaction.owner_id == user.get('id'),
        Transaction.id == transaction_id
    ).first()
    
    if transaction is None:
        raise HTTPException(status_code=404, detail='Transaction not found')
        
    db.delete(transaction)
    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Transaction deleted successfully'})