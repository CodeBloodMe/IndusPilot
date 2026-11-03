from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_org_id
from app.models.entities import Product, BillOfMaterials
from app.schemas.domain import ProductCreate, ProductUpdate, ProductOut

router = APIRouter()


@router.get("", response_model=List[ProductOut])
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    query = db.query(Product).filter(Product.organization_id == org_id)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    if category:
        query = query.filter(Product.category == category)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(Product.name.ilike(s), Product.code.ilike(s), Product.description.ilike(s)))

    products = query.order_by(Product.code.asc()).all()
    results = []
    for p in products:
        active_bom = next((b for b in p.boms if b.is_active), None)
        item_count = len(active_bom.items) if active_bom else 0
        results.append(ProductOut(
            id=p.id,
            organization_id=p.organization_id,
            code=p.code,
            name=p.name,
            category=p.category,
            description=p.description,
            manufacturing_process=p.manufacturing_process,
            base_unit=p.base_unit or "units",
            default_batch_size=p.default_batch_size or 500.0,
            estimated_duration_hours=p.estimated_duration_hours or 24.0,
            is_active=p.is_active,
            active_bom_id=active_bom.id if active_bom else None,
            active_bom_version=active_bom.version if active_bom else None,
            boms_count=len(p.boms),
            components_count=item_count,
            created_at=p.created_at.isoformat() if p.created_at else None
        ))
    return results


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    existing = db.query(Product).filter(
        Product.organization_id == org_id,
        Product.code.ilike(payload.code.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Product with code '{payload.code}' already exists.")

    product = Product(
        organization_id=org_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        category=payload.category,
        description=payload.description,
        manufacturing_process=payload.manufacturing_process,
        base_unit=payload.base_unit,
        default_batch_size=payload.default_batch_size,
        estimated_duration_hours=payload.estimated_duration_hours,
        is_active=payload.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return ProductOut(
        id=product.id,
        organization_id=product.organization_id,
        code=product.code,
        name=product.name,
        category=product.category,
        description=product.description,
        manufacturing_process=product.manufacturing_process,
        base_unit=product.base_unit,
        default_batch_size=product.default_batch_size,
        estimated_duration_hours=product.estimated_duration_hours,
        is_active=product.is_active,
        active_bom_id=None,
        active_bom_version=None,
        boms_count=0,
        components_count=0,
        created_at=product.created_at.isoformat()
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    product = db.query(Product).filter(Product.id == product_id, Product.organization_id == org_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    active_bom = next((b for b in product.boms if b.is_active), None)
    item_count = len(active_bom.items) if active_bom else 0

    return ProductOut(
        id=product.id,
        organization_id=product.organization_id,
        code=product.code,
        name=product.name,
        category=product.category,
        description=product.description,
        manufacturing_process=product.manufacturing_process,
        base_unit=product.base_unit or "units",
        default_batch_size=product.default_batch_size or 500.0,
        estimated_duration_hours=product.estimated_duration_hours or 24.0,
        is_active=product.is_active,
        active_bom_id=active_bom.id if active_bom else None,
        active_bom_version=active_bom.version if active_bom else None,
        boms_count=len(product.boms),
        components_count=item_count,
        created_at=product.created_at.isoformat() if product.created_at else None
    )


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    product = db.query(Product).filter(Product.id == product_id, Product.organization_id == org_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(product, field, val)

    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)

    active_bom = next((b for b in product.boms if b.is_active), None)
    item_count = len(active_bom.items) if active_bom else 0

    return ProductOut(
        id=product.id,
        organization_id=product.organization_id,
        code=product.code,
        name=product.name,
        category=product.category,
        description=product.description,
        manufacturing_process=product.manufacturing_process,
        base_unit=product.base_unit or "units",
        default_batch_size=product.default_batch_size or 500.0,
        estimated_duration_hours=product.estimated_duration_hours or 24.0,
        is_active=product.is_active,
        active_bom_id=active_bom.id if active_bom else None,
        active_bom_version=active_bom.version if active_bom else None,
        boms_count=len(product.boms),
        components_count=item_count,
        created_at=product.created_at.isoformat() if product.created_at else None
    )

