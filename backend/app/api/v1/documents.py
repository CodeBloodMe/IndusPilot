import os
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_org_id
from app.core.config import settings
from app.models.entities import UploadedDocument, Supplier, Material, SupplierQuotation
from app.schemas.domain import DocumentOut
from app.services.document_parser import parse_uploaded_quotation_file

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
MAX_FILE_SIZE = 25 * 1024 * 1024 # 25 MB


def _get_catalogue_dicts(db: Session, org_id: str) -> List[Dict[str, Any]]:
    materials = db.query(Material).filter(Material.organization_id == org_id, Material.is_active == True).all()
    return [
        {
            "id": m.id,
            "code": m.code,
            "name": m.name,
            "grade": m.grade,
            "category": m.category,
            "unit": m.unit,
            "standard_cost": m.standard_cost,
            "manufacturing_forms": m.manufacturing_forms
        }
        for m in materials
    ]


def _get_existing_quote_numbers(db: Session, org_id: str) -> List[str]:
    quotes = db.query(SupplierQuotation.quotation_number).filter(
        SupplierQuotation.organization_id == org_id
    ).all()
    return [q[0] for q in quotes if q[0]]


@router.get("", response_model=List[DocumentOut])
def list_documents(
    validation_status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Lists all uploaded quotation documents with extraction status, quality gate flags, and supplier references."""
    query = db.query(UploadedDocument).filter(UploadedDocument.organization_id == org_id)

    if validation_status:
        query = query.filter(UploadedDocument.validation_status == validation_status)
    if supplier_id:
        query = query.filter(UploadedDocument.supplier_id == supplier_id)

    docs = query.order_by(UploadedDocument.created_at.desc()).all()

    results = []
    for d in docs:
        supplier_name = d.supplier.name if d.supplier else None
        if not supplier_name and d.extraction_result_json:
            supplier_name = d.extraction_result_json.get("supplier_name")

        results.append(DocumentOut(
            id=d.id,
            organization_id=d.organization_id,
            supplier_id=d.supplier_id,
            supplier_name=supplier_name,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size or 0,
            processing_status=d.processing_status or "COMPLETED",
            validation_status=d.validation_status or d.status or "READY_FOR_REVIEW",
            status=d.status or "PENDING_REVIEW",
            confidence_score=d.confidence_score or 0.0,
            error_message=d.error_message,
            created_at=d.created_at.isoformat() if d.created_at else None
        ))
    return results


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """
    Multi-file document ingestion endpoint.
    Uploads quotation documents (PDF, Excel, CSV, Images), validates security and format constraints,
    runs automated extraction, links to suppliers and materials, and subjects output to Quality Gate.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    catalogue = _get_catalogue_dicts(db, org_id)
    existing_quote_nos = _get_existing_quote_numbers(db, org_id)

    processed_results = []

    for file in files:
        raw_filename = file.filename or "uploaded_quotation.pdf"
        safe_filename = os.path.basename(raw_filename).replace(" ", "_")
        ext = os.path.splitext(safe_filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}' for file '{raw_filename}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        save_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(save_path)
        if file_size > MAX_FILE_SIZE:
            try:
                os.remove(save_path)
            except OSError:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"File '{raw_filename}' exceeds the maximum allowed size limit of 25MB."
            )

        # Execute Document Extraction Engine
        extraction = parse_uploaded_quotation_file(
            file_path=save_path,
            original_filename=raw_filename,
            catalogue_materials=catalogue,
            existing_quotation_numbers=existing_quote_nos
        )

        # Match Supplier in DB if recognized
        detected_supplier_name = extraction.get("supplier_name", "")
        supplier_id = None
        if detected_supplier_name and detected_supplier_name != "Unknown Supplier":
            found_supp = db.query(Supplier).filter(
                Supplier.organization_id == org_id,
                Supplier.name.ilike(f"%{detected_supplier_name.strip()}%")
            ).first()
            if found_supp:
                supplier_id = found_supp.id

        # Persist Document Ledger Record
        doc = UploadedDocument(
            organization_id=org_id,
            supplier_id=supplier_id,
            filename=safe_filename,
            file_path=save_path,
            file_type=ext.replace(".", "").upper(),
            file_size=file_size,
            processing_status="COMPLETED",
            validation_status=extraction.get("validation_status", "READY_FOR_REVIEW"),
            status=extraction.get("validation_status", "READY_FOR_REVIEW"),
            confidence_score=extraction.get("confidence_score", 0.0),
            error_message=extraction.get("error"),
            extraction_result_json=extraction,
            raw_text=extraction.get("raw_text_snippet", "")
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        extraction["document_id"] = doc.id
        extraction["supplier_id"] = supplier_id
        processed_results.append(extraction)

    # If single upload, return single dict for ease of client consumption, else list
    if len(processed_results) == 1:
        return processed_results[0]
    return {
        "uploaded_count": len(processed_results),
        "results": processed_results
    }


@router.get("/{document_id}")
def get_document_details(
    document_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves document record metadata and current processing state."""
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id,
        UploadedDocument.organization_id == org_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation document not found.")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "supplier_id": doc.supplier_id,
        "supplier_name": doc.supplier.name if doc.supplier else None,
        "processing_status": doc.processing_status,
        "validation_status": doc.validation_status,
        "confidence_score": doc.confidence_score,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None
    }


@router.get("/{document_id}/extraction")
def get_document_extraction(
    document_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Retrieves immutable machine extraction data and matched material candidates for human review."""
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id,
        UploadedDocument.organization_id == org_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation document not found.")

    if not doc.extraction_result_json:
        raise HTTPException(status_code=400, detail="Document has no extraction payload recorded.")

    result = dict(doc.extraction_result_json)
    result["document_id"] = doc.id
    result["supplier_id"] = doc.supplier_id
    return result


@router.post("/{document_id}/retry")
def retry_document_extraction(
    document_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org_id)
):
    """Re-executes document extraction against the active material catalogue and updates validation state."""
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id,
        UploadedDocument.organization_id == org_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation document not found.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Underlying document file not found on disk.")

    catalogue = _get_catalogue_dicts(db, org_id)
    existing_quote_nos = _get_existing_quote_numbers(db, org_id)

    extraction = parse_uploaded_quotation_file(
        file_path=doc.file_path,
        original_filename=doc.filename,
        catalogue_materials=catalogue,
        existing_quotation_numbers=existing_quote_nos
    )

    doc.extraction_result_json = extraction
    doc.confidence_score = extraction.get("confidence_score", 0.0)
    doc.validation_status = extraction.get("validation_status", "READY_FOR_REVIEW")
    doc.status = doc.validation_status
    doc.error_message = extraction.get("error")

    db.commit()
    db.refresh(doc)

    extraction["document_id"] = doc.id
    return extraction

