from fastapi import status
from fastapi.testclient import TestClient
from main import app
from router.auth import get_current_user
from database import SessionLocal
from models import Transaction

client = TestClient(app)

def override_get_current_user():
    return {
        'id': 1,
        'username': 'testuser'
    }

app.dependency_overrides[get_current_user] = override_get_current_user

def setup_test_data():
    db = SessionLocal()
    db.query(Transaction).filter(Transaction.id == 99).delete()
    db.commit()

    transaction = Transaction(
        id=99,
        title='Initial Salary',
        amount=5000.0,
        type='income',
        category='Job',
        date='2026-08-08',
        owner_id=1
    )

    db.add(transaction)
    db.commit()
    db.close()


def test_get_all_transactions():
    setup_test_data()
    response = client.get('/transactions')
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_get_specific_transaction():
    setup_test_data()
    response = client.get('/transactions/99')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['title'] == 'Initial Salary'


def test_create_transaction():
    db = SessionLocal()
    db.query(Transaction).filter(Transaction.title == 'New Snacks').delete()
    db.commit()
    db.close()

    request_data = {
        "title": "New Snacks",
        "amount": 120.0,
        "type": "expense",
        "category": "Food",
        "date": "2026-08-08"
    }

    response = client.post('/transactions', json=request_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['title'] == 'New Snacks'


def test_update_transaction():
    setup_test_data()

    request_data = {
        "title": "Updated Salary",
        "amount": 6000.0
    }

    response = client.put('/transactions/99', json=request_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['title'] == 'Updated Salary'


def test_delete_transaction():
    setup_test_data()

    response = client.delete('/transactions/99')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'message': 'Transaction deleted successfully'}