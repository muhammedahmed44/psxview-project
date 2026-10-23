"""Authenticated portfolio CRUD and deterministic market calculations."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from auth import get_current_user
from db import get_db
from models import PortfolioHolding, User
import ai

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

class HoldingIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0, le=10_000_000)
    average_price: float = Field(gt=0, le=10_000_000)

def _market():
    from main import get_companies
    rows = {str(c.get("symbol", "")).upper(): c for c in get_companies()}
    return rows

def _payload(db: Session, user: User):
    market = _market()
    rows = db.scalars(select(PortfolioHolding).where(PortfolioHolding.user_id == user.id).order_by(PortfolioHolding.id)).all()
    items, invested, current = [], 0.0, 0.0
    sectors = {}
    for row in rows:
        symbol = row.symbol.upper(); quote = market.get(symbol, {})
        price = quote.get("price") if isinstance(quote.get("price"), (int, float)) and quote.get("price", 0) > 0 else None
        inv = row.quantity * row.average_price; invested += inv
        value = row.quantity * price if price is not None else None
        if value is not None: current += value
        sector = quote.get("sector") or "Unknown / unavailable"
        if value is not None: sectors[sector] = sectors.get(sector, 0) + value
        items.append({"id": row.id, "symbol": symbol, "quantity": row.quantity, "average_price": row.average_price,
                      "latest_price": price, "price_status": "available" if price is not None else "missing/unavailable",
                      "sector": sector, "invested": round(inv, 2), "current_value": round(value, 2) if value is not None else None,
                      "pnl": round(value - inv, 2) if value is not None else None})
    pnl = current - invested if items and current else None
    return {"holdings": items, "metrics": {"invested": round(invested, 2), "current_value": round(current, 2) if current else None,
            "pnl": round(pnl, 2) if pnl is not None else None, "pnl_pct": round(pnl / invested * 100, 2) if pnl is not None and invested else None},
            "sectors": [{"sector": k, "value": round(v, 2), "percentage": round(v / current * 100, 2) if current else 0} for k, v in sectors.items()],
            "as_of": datetime.now(timezone.utc).isoformat()}

def _get(db, user, item_id):
    row = db.get(PortfolioHolding, item_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Holding not found")
    return row

@router.get("")
def list_portfolio(user: User = Depends(get_current_user), db: Session = Depends(get_db)): return _payload(db, user)

@router.post("", status_code=201)
def add(body: HoldingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = PortfolioHolding(user_id=user.id, symbol=body.symbol.upper(), quantity=body.quantity, average_price=body.average_price)
    db.add(row); db.commit(); return _payload(db, user)["holdings"][-1]

@router.put("/{item_id}")
def update(item_id: int, body: HoldingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _get(db, user, item_id); row.symbol = body.symbol.upper(); row.quantity = body.quantity; row.average_price = body.average_price
    db.commit(); return next(x for x in _payload(db, user)["holdings"] if x["id"] == item_id)

@router.delete("/{item_id}")
def remove(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get(db, user, item_id)); db.commit(); return {"ok": True}

@router.post("/analyze")
def analyze(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = _payload(db, user)
    from main import get_news
    news, _ = get_news()
    facts = [f"Invested: PKR {data['metrics']['invested']:,.0f}", f"Holdings: {len(data['holdings'])}"]
    prompt = "Analyze this portfolio using only these facts. Explain concentration, sectors, missing prices, and beginner risk controls. Never promise returns or invent news. Educational only.\n" + str({"portfolio": data, "news": news[:5]})
    result = ai.explain({"symbol": "portfolio", "eps": 1, "price": 1, "years": 5, "growth_pct": 0, "terminal_pct": 0}, {"required_return_pct": 0, "implied_growth_pct": 0, "fair_value": 1, "upside_pct": 0})
    return {"text": result["text"] + "\n\nPortfolio facts: " + "; ".join(facts), "source": result["source"], "facts": facts}
