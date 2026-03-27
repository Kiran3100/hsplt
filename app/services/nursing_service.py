"""
Nursing Service
Handles nursing-specific business logic including patient care, vital signs, and nursing notes.
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.user import User
from app.models.patient import PatientProfile, MedicalRecord, Appointment, Admission, PatientDocument
from app.models.hospital import Department, StaffDepartmentAssignment
from app.models.nurse import NurseProfile
from app.core.enums import UserRole, DocumentType
from app.core.utils import generate_patient_ref


class NursingService:
    """Service for nursing operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================================
    # USER CONTEXT AND VALIDATION
    # ============================================================================
    
    def get_user_context(self, current_user: User) -> dict:
        """Extract user context from JWT token"""
        user_roles = [role.name for role in current_user.roles]
        
        return {
            "user_id": str(current_user.id),
            "hospital_id": str(current_user.hospital_id),
            "role": user_roles[0] if user_roles else None,
            "all_roles": user_roles
        }
    
    async def validate_nurse_access(self, user_context: dict) -> None:
        """Ensure user is a nurse"""
        if user_context["role"] != UserRole.NURSE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - Nurse role required"
            )
    
    async def get_nurse_profile(self, user_context: dict):
        """Get nurse profile with department information"""
        await self.validate_nurse_access(user_context)
        
        # Get nurse profile directly
        result = await self.db.execute(
            select(NurseProfile)
            .where(NurseProfile.user_id == user_context["user_id"])
            .options(
                selectinload(NurseProfile.user),
                selectinload(NurseProfile.department)
            )
        )
        
        nurse_profile = result.scalar_one_or_none()
        
        # If no NurseProfile exists, try StaffDepartmentAssignment as fallback
        if not nurse_profile:
            # Get nurse user
            user_result = await self.db.execute(
                select(User)
                .where(User.id == user_context["user_id"])
            )
            
            nurse_user = user_result.scalar_one_or_none()
            if not nurse_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nurse user not found"
                )
            
            # Get nurse's department assignment
            dept_result = await self.db.execute(
                select(StaffDepartmentAssignment)
                .where(
                    and_(
                        StaffDepartmentAssignment.staff_id == user_context["user_id"],
                        StaffDepartmentAssignment.is_active == True
                    )
                )
                .options(selectinload(StaffDepartmentAssignment.department))
            )
            
            assignment = dept_result.scalar_one_or_none()
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nurse profile or department assignment not found. Please ensure the nurse is properly registered with a department."
                )
            
            # Create a mock object that has the same interface as NurseProfile
            class MockNurseProfile:
                def __init__(self, user, department):
                    self.user = user
                    self.department = department
                    self.department_id = department.id
                    self.hospital_id = user.hospital_id
            
            return MockNurseProfile(nurse_user, assignment.department)
        
        return nurse_profile
    
    # ============================================================================
    # PATIENT MANAGEMENT
    # ============================================================================
    
    async def get_patients_list(self, filters: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Get list of patients for nursing care in nurse's assigned department"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Build query for patients with appointments/admissions in nurse's department
        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        search = filters.get("search")
        offset = (page - 1) * limit
        
        # Subquery for patients with appointments in this department
        appointment_patients = select(Appointment.patient_id).where(
            Appointment.department_id == nurse.department_id
        ).distinct()
        
        # Subquery for patients with admissions in this department
        admission_patients = select(Admission.patient_id).where(
            Admission.department_id == nurse.department_id
        ).distinct()
        
        # Main query for patients
        query = select(PatientProfile).where(
            and_(
                PatientProfile.hospital_id == nurse.hospital_id,
                or_(
                    PatientProfile.id.in_(appointment_patients),
                    PatientProfile.id.in_(admission_patients)
                )
            )
        ).options(
            selectinload(PatientProfile.user)
        ).order_by(PatientProfile.created_at.desc())
        
        # Apply search filter
        if search:
            query = query.join(User).where(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    PatientProfile.patient_id.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_query = select(func.count(PatientProfile.id.distinct())).where(
            and_(
                PatientProfile.hospital_id == nurse.hospital_id,
                or_(
                    PatientProfile.id.in_(appointment_patients),
                    PatientProfile.id.in_(admission_patients)
                )
            )
        )
        if search:
            count_query = count_query.join(User).where(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    PatientProfile.patient_id.ilike(f"%{search}%")
                )
            )
        
        total_result = await self.db.execute(count_query)
        total_patients = total_result.scalar() or 0
        
        # Get paginated patients
        patients_result = await self.db.execute(query.offset(offset).limit(limit))
        patients = patients_result.scalars().all()
        
        # Format response
        from app.schemas.clinical import PatientProfileViewOut
        patient_list = []
        for patient in patients:
            # Get current admission info if exists in this department
            admission_result = await self.db.execute(
                select(Admission)
                .where(
                    and_(
                        Admission.patient_id == patient.id,
                        Admission.department_id == nurse.department_id,
                        Admission.is_active == True
                    )
                )
                .options(
                    selectinload(Admission.doctor)
                )
                .limit(1)
            )
            admission = admission_result.scalar_one_or_none()
            
            # Build emergency contact dict only if all required fields are present
            emergency_contact = None
            if patient.emergency_contact_name and patient.emergency_contact_phone and patient.emergency_contact_relation:
                emergency_contact = {
                    "name": patient.emergency_contact_name,
                    "phone": patient.emergency_contact_phone,
                    "relation": patient.emergency_contact_relation
                }
            
            patient_list.append(PatientProfileViewOut(
                patient_ref=patient.patient_id,
                patient_name=f"{patient.user.first_name} {patient.user.last_name}",
                date_of_birth=patient.date_of_birth,
                gender=patient.gender,
                blood_group=patient.blood_group,
                allergies=patient.allergies or [],
                chronic_conditions=patient.chronic_conditions or [],
                current_medications=patient.current_medications or [],
                emergency_contact=emergency_contact,
                admission_status="ADMITTED" if admission else "OUTPATIENT",
                room_number=admission.room_number if admission else None,
                bed_number=admission.bed_number if admission else None,
                attending_doctor=f"{admission.doctor.first_name} {admission.doctor.last_name}" if admission and admission.doctor else None
            ))
        
        return {
            "department": nurse.department.name,
            "patients": patient_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_patients,
                "pages": (total_patients + limit - 1) // limit
            }
        }
    
    async def get_patient_profile(self, patient_ref: str, current_user: User) -> Dict[str, Any]:
        """Get detailed patient profile for nursing care"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Get current admission info in this department
        admission_result = await self.db.execute(
            select(Admission)
            .where(
                and_(
                    Admission.patient_id == patient.id,
                    Admission.department_id == nurse.department_id,
                    Admission.is_active == True
                )
            )
            .options(
                selectinload(Admission.doctor),
                selectinload(Admission.department)
            )
            .limit(1)
        )
        admission = admission_result.scalar_one_or_none()
        
        # Get recent vital signs
        vitals_result = await self.db.execute(
            select(MedicalRecord.vital_signs, MedicalRecord.created_at)
            .where(MedicalRecord.patient_id == patient.id)
            .order_by(desc(MedicalRecord.created_at))
            .limit(1)
        )
        recent_vitals = vitals_result.first()
        
        # Build emergency contact dict only if all required fields are present
        emergency_contact = None
        if patient.emergency_contact_name and patient.emergency_contact_phone and patient.emergency_contact_relation:
            emergency_contact = {
                "name": patient.emergency_contact_name,
                "phone": patient.emergency_contact_phone,
                "relation": patient.emergency_contact_relation
            }
        
        return {
            "patient_ref": patient.patient_id,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "date_of_birth": patient.date_of_birth,
            "gender": patient.gender,
            "blood_group": patient.blood_group,
            "allergies": patient.allergies or [],
            "chronic_conditions": patient.chronic_conditions or [],
            "current_medications": patient.current_medications or [],
            "emergency_contact": emergency_contact,
            "nurse_department": nurse.department.name,
            "admission_info": {
                "status": "ADMITTED" if admission else "OUTPATIENT",
                "admission_number": admission.admission_number if admission else None,
                "admission_date": admission.admission_date.isoformat() if admission else None,
                "department": admission.department.name if admission and admission.department else None,
                "attending_doctor": f"{admission.doctor.first_name} {admission.doctor.last_name}" if admission and admission.doctor else None,
                "ward": admission.ward if admission else None,
                "room_number": admission.room_number if admission else None,
                "bed_number": admission.bed_number if admission else None
            },
            "recent_vitals": {
                "recorded_at": recent_vitals.created_at.isoformat() if recent_vitals else None,
                "vitals": recent_vitals.vital_signs if recent_vitals else {}
            }
        }
    
    # ============================================================================
    # VITAL SIGNS MANAGEMENT
    # ============================================================================
    
    async def update_patient_vitals(self, patient_ref: str, vitals_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Update patient vital signs"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Prepare vital signs data
        vital_signs = {}
        if vitals_data.get("blood_pressure_systolic") and vitals_data.get("blood_pressure_diastolic"):
            vital_signs["blood_pressure"] = f"{vitals_data['blood_pressure_systolic']}/{vitals_data['blood_pressure_diastolic']}"
        if vitals_data.get("pulse_rate"):
            vital_signs["pulse_rate"] = vitals_data["pulse_rate"]
        if vitals_data.get("temperature"):
            vital_signs["temperature"] = vitals_data["temperature"]
        if vitals_data.get("respiratory_rate"):
            vital_signs["respiratory_rate"] = vitals_data["respiratory_rate"]
        if vitals_data.get("oxygen_saturation"):
            vital_signs["oxygen_saturation"] = vitals_data["oxygen_saturation"]
        if vitals_data.get("weight"):
            vital_signs["weight"] = vitals_data["weight"]
        if vitals_data.get("height"):
            vital_signs["height"] = vitals_data["height"]
        if vitals_data.get("pain_scale"):
            vital_signs["pain_scale"] = vitals_data["pain_scale"]
        
        # Create medical record for vital signs
        # Note: doctor_id is required by DB constraint, using nurse's user_id as workaround
        medical_record = MedicalRecord(
            id=uuid.uuid4(),
            hospital_id=user_context["hospital_id"],
            patient_id=patient.id,
            doctor_id=user_context["user_id"],  # Using nurse's user_id (DB constraint requires non-null)
            chief_complaint="Vital Signs Assessment by Nurse",
            vital_signs=vital_signs,
            examination_findings=vitals_data.get("notes"),
            is_finalized=True  # Vital signs are immediately finalized
        )
        
        # Add recorded_by information to vital signs
        vital_signs["recorded_by"] = f"{current_user.first_name} {current_user.last_name} (Nurse)"
        vital_signs["recorded_at"] = datetime.utcnow().isoformat()
        medical_record.vital_signs = vital_signs
        
        self.db.add(medical_record)
        await self.db.commit()
        
        return {
            "patient_ref": patient_ref,
            "vitals_recorded": True,
            "recorded_by": f"{current_user.first_name} {current_user.last_name}",
            "recorded_at": datetime.utcnow().isoformat(),
            "message": "Vital signs updated successfully"
        }
    
    async def get_patient_vitals_history(self, patient_ref: str, days: int, current_user: User) -> Dict[str, Any]:
        """Get patient vital signs history"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Get vital signs from medical records
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.vital_signs.isnot(None),
                    MedicalRecord.created_at >= start_date
                )
            )
            .order_by(desc(MedicalRecord.created_at))
        )
        
        records = result.scalars().all()
        
        # Helper function to safely parse numeric values from strings
        def parse_numeric(value, value_type=float):
            """Parse numeric value, handling strings with units"""
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return value_type(value)
            if isinstance(value, str):
                # Remove common units and whitespace
                cleaned = value.strip()
                cleaned = cleaned.replace('F', '').replace('C', '')  # Temperature
                cleaned = cleaned.replace('%', '')  # Percentage
                cleaned = cleaned.replace('/min', '')  # Rate
                cleaned = cleaned.replace('bpm', '')  # Beats per minute
                cleaned = cleaned.replace('kg', '').replace('lbs', '')  # Weight
                cleaned = cleaned.replace('cm', '').replace('in', '')  # Height
                cleaned = cleaned.strip()
                try:
                    return value_type(float(cleaned)) if value_type == int else value_type(cleaned)
                except (ValueError, TypeError):
                    return None
            return None
        
        # Format vital signs history
        from app.schemas.clinical import VitalSignsHistoryOut
        vitals_history = []
        for record in records:
            if record.vital_signs:
                vitals = record.vital_signs
                vitals_history.append(VitalSignsHistoryOut(
                    recorded_at=record.created_at.isoformat(),
                    recorded_by=vitals.get("recorded_by", "Unknown"),
                    blood_pressure=vitals.get("blood_pressure"),
                    pulse_rate=parse_numeric(vitals.get("pulse_rate"), int),
                    temperature=parse_numeric(vitals.get("temperature"), float),
                    respiratory_rate=parse_numeric(vitals.get("respiratory_rate"), int),
                    oxygen_saturation=parse_numeric(vitals.get("oxygen_saturation"), int),
                    weight=parse_numeric(vitals.get("weight"), float),
                    height=parse_numeric(vitals.get("height"), float),
                    pain_scale=parse_numeric(vitals.get("pain_scale"), int),
                    notes=record.examination_findings
                ))
        
        return {
            "patient_ref": patient_ref,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "history_days": days,
            "vitals_history": vitals_history
        }
    
    # ============================================================================
    # NURSING NOTES MANAGEMENT
    # ============================================================================
    
    async def add_nursing_note(self, patient_ref: str, note_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Add nursing note for patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Create nursing note as medical record
        # Note: doctor_id is required by DB constraint, using nurse's user_id as workaround
        medical_record = MedicalRecord(
            id=uuid.uuid4(),
            hospital_id=user_context["hospital_id"],
            patient_id=patient.id,
            doctor_id=user_context["user_id"],  # Using nurse's user_id (DB constraint requires non-null)
            chief_complaint=f"Nursing Note - {note_data['note_type']}",
            examination_findings=note_data["note_content"],
            vital_signs={
                "note_type": note_data["note_type"],
                "priority": note_data["priority"],
                "follow_up_required": note_data["follow_up_required"],
                "recorded_by": f"{current_user.first_name} {current_user.last_name} (Nurse)",
                "recorded_at": datetime.utcnow().isoformat()
            },
            is_finalized=True
        )
        
        self.db.add(medical_record)
        await self.db.commit()
        
        return {
            "note_id": str(medical_record.id),
            "patient_ref": patient_ref,
            "note_type": note_data["note_type"],
            "priority": note_data["priority"],
            "recorded_by": f"{current_user.first_name} {current_user.last_name}",
            "recorded_at": datetime.utcnow().isoformat(),
            "message": "Nursing note added successfully"
        }
    
    async def get_nursing_notes(self, patient_ref: str, filters: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Get nursing notes for patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Build query for nursing notes (identified by chief_complaint pattern)
        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        note_type = filters.get("note_type")
        offset = (page - 1) * limit
        
        query = select(MedicalRecord).where(
            and_(
                MedicalRecord.patient_id == patient.id,
                MedicalRecord.chief_complaint.like("Nursing Note%")
            )
        ).order_by(desc(MedicalRecord.created_at))
        
        # Apply note type filter
        if note_type:
            query = query.where(MedicalRecord.chief_complaint.like(f"%{note_type}%"))
        
        # Get total count
        count_query = select(func.count(MedicalRecord.id)).where(
            and_(
                MedicalRecord.patient_id == patient.id,
                MedicalRecord.chief_complaint.like("Nursing Note%")
            )
        )
        if note_type:
            count_query = count_query.where(MedicalRecord.chief_complaint.like(f"%{note_type}%"))
        
        total_result = await self.db.execute(count_query)
        total_notes = total_result.scalar() or 0
        
        # Get paginated notes
        notes_result = await self.db.execute(query.offset(offset).limit(limit))
        notes = notes_result.scalars().all()
        
        # Format response
        from app.schemas.clinical import NursingNoteOut
        nursing_notes = []
        for note in notes:
            vitals = note.vital_signs or {}
            nursing_notes.append(NursingNoteOut(
                note_id=str(note.id),
                patient_ref=patient_ref,
                patient_name=f"{patient.user.first_name} {patient.user.last_name}",
                note_type=vitals.get("note_type", "GENERAL"),
                note_content=note.examination_findings or "",
                priority=vitals.get("priority", "NORMAL"),
                follow_up_required=vitals.get("follow_up_required", False),
                recorded_by=vitals.get("recorded_by", "Unknown"),
                recorded_at=note.created_at.isoformat()
            ))
        
        return {
            "patient_ref": patient_ref,
            "nursing_notes": nursing_notes,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_notes,
                "pages": (total_notes + limit - 1) // limit
            }
        }
    
    # ============================================================================
    # DOCUMENT UPLOAD
    # ============================================================================
    
    async def upload_nursing_report(self, patient_ref: str, file_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Upload nursing report for patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Create document record
        document = PatientDocument(
            id=uuid.uuid4(),
            hospital_id=user_context["hospital_id"],
            patient_id=patient.id,
            uploaded_by=user_context["user_id"],
            document_type="MEDICAL_REPORT",  # Use existing enum
            title=f"[NURSING] {file_data['title']}",
            description=f"Nursing Report - {file_data['report_type']}: {file_data.get('description', '')}",
            file_name=file_data["file_name"],
            file_path=file_data["file_path"],
            file_size=file_data["file_size"],
            mime_type=file_data["mime_type"],
            document_date=datetime.utcnow().date().isoformat(),
            is_sensitive=True
        )
        
        self.db.add(document)
        await self.db.commit()
        
        return {
            "document_id": str(document.id),
            "patient_ref": patient_ref,
            "report_type": file_data["report_type"],
            "title": file_data["title"],
            "file_size": file_data["file_size"],
            "uploaded_by": f"{current_user.first_name} {current_user.last_name} (Nurse)",
            "upload_date": document.created_at.isoformat(),
            "message": "Nursing report uploaded successfully"
        }
    
    # ============================================================================
    # DASHBOARD
    # ============================================================================
    
    async def get_nurse_dashboard(self, current_user: User) -> Dict[str, Any]:
        """Get nurse dashboard with key metrics and information"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patients in nurse's department (via appointments/admissions)
        # Subquery for patients with appointments in this department
        appointment_patients = select(Appointment.patient_id).where(
            Appointment.department_id == nurse.department_id
        ).distinct()
        
        # Subquery for patients with admissions in this department
        admission_patients = select(Admission.patient_id).where(
            Admission.department_id == nurse.department_id
        ).distinct()
        
        # Get total patients in this department
        total_patients_result = await self.db.execute(
            select(func.count(PatientProfile.id.distinct()))
            .where(
                and_(
                    PatientProfile.hospital_id == nurse.hospital_id,
                    or_(
                        PatientProfile.id.in_(appointment_patients),
                        PatientProfile.id.in_(admission_patients)
                    )
                )
            )
        )
        total_patients = total_patients_result.scalar() or 0
        
        # Get admitted patients in this department
        admitted_patients_result = await self.db.execute(
            select(func.count(Admission.id))
            .where(
                and_(
                    Admission.hospital_id == nurse.hospital_id,
                    Admission.department_id == nurse.department_id,
                    Admission.is_active == True
                )
            )
        )
        admitted_patients = admitted_patients_result.scalar() or 0
        
        # Get today's vital signs entries by this nurse
        today = datetime.utcnow().date()
        vitals_today_result = await self.db.execute(
            select(func.count(MedicalRecord.id))
            .where(
                and_(
                    MedicalRecord.hospital_id == nurse.hospital_id,
                    MedicalRecord.chief_complaint == "Vital Signs Assessment by Nurse",
                    func.date(MedicalRecord.created_at) == today
                )
            )
        )
        vitals_today = vitals_today_result.scalar() or 0
        
        # Get today's nursing notes by this nurse
        notes_today_result = await self.db.execute(
            select(func.count(MedicalRecord.id))
            .where(
                and_(
                    MedicalRecord.hospital_id == nurse.hospital_id,
                    MedicalRecord.chief_complaint.like("Nursing Note%"),
                    func.date(MedicalRecord.created_at) == today
                )
            )
        )
        notes_today = notes_today_result.scalar() or 0
        
        # Get recent patients with high priority notes in this department
        # Note: Removed .contains() filter as it causes JSONB query issues
        high_priority_result = await self.db.execute(
            select(MedicalRecord, PatientProfile)
            .join(PatientProfile, MedicalRecord.patient_id == PatientProfile.id)
            .where(
                and_(
                    MedicalRecord.hospital_id == nurse.hospital_id,
                    MedicalRecord.created_at >= datetime.utcnow() - timedelta(days=1),
                    or_(
                        PatientProfile.id.in_(appointment_patients),
                        PatientProfile.id.in_(admission_patients)
                    )
                )
            )
            .options(selectinload(PatientProfile.user))
            .order_by(desc(MedicalRecord.created_at))
            .limit(5)
        )
        
        high_priority_patients = []
        for record, patient in high_priority_result:
            vitals = record.vital_signs or {}
            high_priority_patients.append({
                "patient_ref": patient.patient_id,
                "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
                "note_type": vitals.get("note_type", "GENERAL"),
                "priority": vitals.get("priority", "NORMAL"),
                "recorded_at": record.created_at.isoformat(),
                "follow_up_required": vitals.get("follow_up_required", False)
            })
        
        return {
            "nurse_name": f"{current_user.first_name} {current_user.last_name}",
            "hospital_id": user_context["hospital_id"],
            "department": nurse.department.name,
            "department_id": str(nurse.department_id),
            "dashboard_date": datetime.utcnow().date().isoformat(),
            "statistics": {
                "department_patients": total_patients,
                "admitted_patients": admitted_patients,
                "vitals_recorded_today": vitals_today,
                "nursing_notes_today": notes_today
            },
            "high_priority_patients": high_priority_patients,
            "quick_actions": [
                "Record vital signs",
                "Add nursing note",
                "Upload nursing report",
                "View patient profiles"
            ]
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    async def get_patient_by_ref_with_department_check(self, patient_ref: str, nurse) -> PatientProfile:
        """Get patient by reference with department access control"""
        # Get patient
        patient_result = await self.db.execute(
            select(PatientProfile)
            .where(
                and_(
                    PatientProfile.patient_id == patient_ref,
                    PatientProfile.hospital_id == nurse.hospital_id
                )
            )
            .options(selectinload(PatientProfile.user))
        )
        
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_ref} not found"
            )
        
        # Check if patient has any connection to nurse's department
        # Check appointments in this department
        appointment_check = await self.db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.patient_id == patient.id,
                    Appointment.department_id == nurse.department_id
                )
            )
            .limit(1)
        )
        
        # Check current or recent admissions in nurse's department
        admission_check = await self.db.execute(
            select(Admission)
            .where(
                and_(
                    Admission.patient_id == patient.id,
                    Admission.department_id == nurse.department_id
                )
            )
            .limit(1)
        )
        
        if not appointment_check.scalar_one_or_none() and not admission_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied - Patient not associated with your department ({nurse.department.name})"
            )
        
        return patient

    # ============================================================================
    # MEDICATION ADMINISTRATION TRACKING
    # ============================================================================
    
    async def record_medication_administration(self, patient_ref: str, med_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Record medication administration for a patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Create medication administration record as medical record
        administered_at = med_data.get("administered_at") or datetime.utcnow().isoformat()
        
        # Note: doctor_id is required by DB constraint, using nurse's user_id as workaround
        medical_record = MedicalRecord(
            id=uuid.uuid4(),
            hospital_id=user_context["hospital_id"],
            patient_id=patient.id,
            doctor_id=user_context["user_id"],  # Using nurse's user_id (DB constraint requires non-null)
            chief_complaint="Medication Administration",
            examination_findings=med_data.get("notes", ""),
            vital_signs={
                "medication_administration": {
                    "prescription_id": med_data["prescription_id"],
                    "medicine_name": med_data["medicine_name"],
                    "dosage": med_data["dosage"],
                    "route": med_data["route"],
                    "administered_at": administered_at,
                    "patient_response": med_data.get("patient_response"),
                    "administered_by": f"{current_user.first_name} {current_user.last_name} (Nurse)",
                    "nurse_id": user_context["user_id"]
                }
            },
            is_finalized=True
        )
        
        self.db.add(medical_record)
        await self.db.commit()
        
        return {
            "record_id": str(medical_record.id),
            "patient_ref": patient_ref,
            "medicine_name": med_data["medicine_name"],
            "dosage": med_data["dosage"],
            "route": med_data["route"],
            "administered_at": administered_at,
            "administered_by": f"{current_user.first_name} {current_user.last_name}",
            "message": "Medication administration recorded successfully"
        }

    async def get_medication_administration_history(self, patient_ref: str, days: int, current_user: User) -> Dict[str, Any]:
        """Get medication administration history for a patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Get medication administration records
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.chief_complaint == "Medication Administration",
                    MedicalRecord.created_at >= start_date
                )
            )
            .order_by(desc(MedicalRecord.created_at))
        )
        
        records = result.scalars().all()
        
        # Format history
        history = []
        for record in records:
            if record.vital_signs and "medication_administration" in record.vital_signs:
                med_data = record.vital_signs["medication_administration"]
                history.append({
                    "record_id": str(record.id),
                    "medicine_name": med_data.get("medicine_name"),
                    "dosage": med_data.get("dosage"),
                    "route": med_data.get("route"),
                    "administered_at": med_data.get("administered_at"),
                    "administered_by": med_data.get("administered_by"),
                    "patient_response": med_data.get("patient_response"),
                    "notes": record.examination_findings
                })
        
        return {
            "patient_ref": patient_ref,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "history_days": days,
            "total_administrations": len(history),
            "medication_history": history
        }

    # ============================================================================
    # DOCTOR ORDERS INTEGRATION
    # ============================================================================
    
    async def get_pending_doctor_orders(self, filters: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Get all pending doctor orders for nurse's department"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # For now, return mock data structure since we don't have a dedicated orders table
        # In production, this would query a doctor_orders table
        return {
            "department": nurse.department.name,
            "pending_orders": [],
            "message": "Doctor orders integration requires dedicated orders table - currently returning empty list",
            "note": "This feature requires database migration to add doctor_orders table"
        }
    
    async def execute_doctor_order(self, order_id: str, execution_notes: Optional[str], current_user: User) -> Dict[str, Any]:
        """Mark a doctor order as executed"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Mock implementation - requires dedicated orders table
        return {
            "order_id": order_id,
            "status": "executed",
            "executed_by": f"{current_user.first_name} {current_user.last_name}",
            "executed_at": datetime.utcnow().isoformat(),
            "execution_notes": execution_notes,
            "message": "Doctor orders integration requires dedicated orders table",
            "note": "This feature requires database migration to add doctor_orders table"
        }
    
    async def get_my_executed_orders(self, filters: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Get orders executed by the current nurse"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Mock implementation - requires dedicated orders table
        return {
            "nurse_name": f"{current_user.first_name} {current_user.last_name}",
            "executed_orders": [],
            "message": "Doctor orders integration requires dedicated orders table - currently returning empty list",
            "note": "This feature requires database migration to add doctor_orders table"
        }

    # ============================================================================
    # VITALS TRENDING AND CHARTS
    # ============================================================================
    
    async def get_vitals_trend(self, patient_ref: str, vital_type: str, days: int, current_user: User) -> Dict[str, Any]:
        """Get vitals trend data for charting"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Get vital signs from medical records
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.vital_signs.isnot(None),
                    MedicalRecord.created_at >= start_date
                )
            )
            .order_by(MedicalRecord.created_at)
        )
        
        records = result.scalars().all()
        
        # Extract trend data for specific vital type
        vital_key_map = {
            "BP": "blood_pressure",
            "PULSE": "pulse_rate",
            "TEMP": "temperature",
            "SPO2": "oxygen_saturation",
            "RR": "respiratory_rate",
            "WEIGHT": "weight"
        }
        
        vital_key = vital_key_map.get(vital_type.upper())
        if not vital_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid vital type: {vital_type}"
            )
        
        trend_data = []
        values = []
        
        for record in records:
            if record.vital_signs and vital_key in record.vital_signs:
                value = record.vital_signs[vital_key]
                trend_data.append({
                    "timestamp": record.created_at.isoformat(),
                    "value": value
                })
                # Extract numeric value for statistics
                if isinstance(value, (int, float)):
                    values.append(value)
        
        # Calculate statistics
        statistics = {}
        if values:
            statistics = {
                "min": min(values),
                "max": max(values),
                "average": sum(values) / len(values),
                "count": len(values)
            }
            
            # Determine trend direction
            if len(values) >= 2:
                first_half = values[:len(values)//2]
                second_half = values[len(values)//2:]
                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)
                
                if avg_second > avg_first * 1.05:
                    statistics["trend"] = "increasing"
                elif avg_second < avg_first * 0.95:
                    statistics["trend"] = "decreasing"
                else:
                    statistics["trend"] = "stable"
        
        return {
            "patient_ref": patient_ref,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "vital_type": vital_type,
            "days": days,
            "trend_data": trend_data,
            "statistics": statistics
        }

    async def get_vitals_summary(self, patient_ref: str, current_user: User) -> Dict[str, Any]:
        """Get comprehensive vitals summary with trends for all vital signs"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Get latest vitals
        latest_result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.vital_signs.isnot(None)
                )
            )
            .order_by(desc(MedicalRecord.created_at))
            .limit(1)
        )
        
        latest_record = latest_result.scalar_one_or_none()
        latest_vitals = latest_record.vital_signs if latest_record else {}
        
        # Get 24-hour trends
        day_ago = datetime.utcnow() - timedelta(days=1)
        day_result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.vital_signs.isnot(None),
                    MedicalRecord.created_at >= day_ago
                )
            )
            .order_by(MedicalRecord.created_at)
        )
        day_records = day_result.scalars().all()
        
        # Get 7-day trends
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.vital_signs.isnot(None),
                    MedicalRecord.created_at >= week_ago
                )
            )
            .order_by(MedicalRecord.created_at)
        )
        week_records = week_result.scalars().all()
        
        return {
            "patient_ref": patient_ref,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "latest_vitals": latest_vitals,
            "latest_recorded_at": latest_record.created_at.isoformat() if latest_record else None,
            "trends_24h": len(day_records),
            "trends_7d": len(week_records),
            "summary": "Comprehensive vitals summary retrieved successfully"
        }

    async def get_vitals_alerts(self, patient_ref: str, current_user: User) -> Dict[str, Any]:
        """Get active vitals alerts for a patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Get latest vitals
        latest_result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.patient_id == patient.id,
                    MedicalRecord.vital_signs.isnot(None)
                )
            )
            .order_by(desc(MedicalRecord.created_at))
            .limit(1)
        )
        
        latest_record = latest_result.scalar_one_or_none()
        
        alerts = []
        
        if latest_record and latest_record.vital_signs:
            vitals = latest_record.vital_signs
            
            # Check for abnormal values (simplified logic)
            if "pulse_rate" in vitals:
                pulse = vitals["pulse_rate"]
                if isinstance(pulse, (int, float)):
                    if pulse < 60:
                        alerts.append({"type": "LOW_PULSE", "value": pulse, "severity": "WARNING"})
                    elif pulse > 100:
                        alerts.append({"type": "HIGH_PULSE", "value": pulse, "severity": "WARNING"})
            
            if "temperature" in vitals:
                temp = vitals["temperature"]
                if isinstance(temp, (int, float)):
                    if temp > 38.0:
                        alerts.append({"type": "FEVER", "value": temp, "severity": "WARNING"})
                    elif temp < 36.0:
                        alerts.append({"type": "HYPOTHERMIA", "value": temp, "severity": "CRITICAL"})
            
            if "oxygen_saturation" in vitals:
                spo2 = vitals["oxygen_saturation"]
                if isinstance(spo2, (int, float)):
                    if spo2 < 95:
                        alerts.append({"type": "LOW_OXYGEN", "value": spo2, "severity": "CRITICAL"})
        
        return {
            "patient_ref": patient_ref,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "alerts": alerts,
            "alert_count": len(alerts),
            "last_vitals_check": latest_record.created_at.isoformat() if latest_record else None
        }

    # ============================================================================
    # SHIFT HANDOVER
    # ============================================================================
    
    async def create_shift_handover(self, handover_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Create shift handover report"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Store handover as a special medical record
        # Note: doctor_id is required by DB constraint, using nurse's user_id as workaround
        handover_record = MedicalRecord(
            id=uuid.uuid4(),
            hospital_id=user_context["hospital_id"],
            patient_id=None,  # Not patient-specific
            doctor_id=user_context["user_id"],  # Using nurse's user_id (DB constraint requires non-null)
            chief_complaint="Shift Handover Report",
            examination_findings=handover_data.get("notes", ""),
            vital_signs={
                "shift_handover": {
                    "shift_type": handover_data["shift_type"],
                    "ward": handover_data["ward"],
                    "patients_count": handover_data["patients_count"],
                    "critical_patients": handover_data.get("critical_patients", []),
                    "pending_tasks": handover_data.get("pending_tasks", []),
                    "completed_tasks": handover_data.get("completed_tasks", []),
                    "incidents": handover_data.get("incidents", []),
                    "created_by": f"{current_user.first_name} {current_user.last_name} (Nurse)",
                    "nurse_id": user_context["user_id"],
                    "department_id": str(nurse.department_id),
                    "department_name": nurse.department.name
                }
            },
            is_finalized=True
        )
        
        self.db.add(handover_record)
        await self.db.commit()
        
        return {
            "handover_id": str(handover_record.id),
            "shift_type": handover_data["shift_type"],
            "ward": handover_data["ward"],
            "created_by": f"{current_user.first_name} {current_user.last_name}",
            "created_at": handover_record.created_at.isoformat(),
            "message": "Shift handover created successfully"
        }

    async def get_latest_shift_handover(self, ward: Optional[str], current_user: User) -> Dict[str, Any]:
        """Get the latest shift handover report"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Query for latest handover
        query = select(MedicalRecord).where(
            and_(
                MedicalRecord.hospital_id == user_context["hospital_id"],
                MedicalRecord.chief_complaint == "Shift Handover Report"
            )
        ).order_by(desc(MedicalRecord.created_at))
        
        # Note: Removed .contains() filter - will filter in Python if needed
        # if ward:
        #     query = query.where(MedicalRecord.vital_signs.contains({"shift_handover": {"ward": ward}}))
        
        result = await self.db.execute(query.limit(10))  # Get more records to filter
        all_records = result.scalars().all()
        
        # Filter by ward in Python if specified
        handover_record = None
        if ward:
            for record in all_records:
                shift_data = record.vital_signs.get("shift_handover", {})
                if shift_data.get("ward") == ward:
                    handover_record = record
                    break
        else:
            handover_record = all_records[0] if all_records else None
        
        if not handover_record:
            return {
                "message": "No shift handover found",
                "handover": None
            }
        
        handover_data = handover_record.vital_signs.get("shift_handover", {})
        
        return {
            "handover_id": str(handover_record.id),
            "shift_type": handover_data.get("shift_type"),
            "ward": handover_data.get("ward"),
            "patients_count": handover_data.get("patients_count"),
            "critical_patients": handover_data.get("critical_patients", []),
            "pending_tasks": handover_data.get("pending_tasks", []),
            "completed_tasks": handover_data.get("completed_tasks", []),
            "incidents": handover_data.get("incidents", []),
            "notes": handover_record.examination_findings,
            "created_by": handover_data.get("created_by"),
            "created_at": handover_record.created_at.isoformat()
        }

    async def get_shift_handover_history(self, filters: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Get shift handover history"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        days = filters.get("days", 7)
        ward = filters.get("ward")
        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        offset = (page - 1) * limit
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query
        query = select(MedicalRecord).where(
            and_(
                MedicalRecord.hospital_id == user_context["hospital_id"],
                MedicalRecord.chief_complaint == "Shift Handover Report",
                MedicalRecord.created_at >= start_date
            )
        ).order_by(desc(MedicalRecord.created_at))
        
        # Note: Removed .contains() filter - will filter in Python if needed
        # if ward:
        #     query = query.where(MedicalRecord.vital_signs.contains({"shift_handover": {"ward": ward}}))
        
        # Get total count
        count_query = select(func.count(MedicalRecord.id)).where(
            and_(
                MedicalRecord.hospital_id == user_context["hospital_id"],
                MedicalRecord.chief_complaint == "Shift Handover Report",
                MedicalRecord.created_at >= start_date
            )
        )
        
        # Note: Removed .contains() filter from count query
        # if ward:
        #     count_query = count_query.where(MedicalRecord.vital_signs.contains({"shift_handover": {"ward": ward}}))
        
        total_result = await self.db.execute(count_query)
        total_handovers = total_result.scalar() or 0
        
        # Get paginated handovers
        handovers_result = await self.db.execute(query.offset(offset).limit(limit * 2))  # Get extra for filtering
        all_handovers = handovers_result.scalars().all()
        
        # Filter by ward in Python if specified
        if ward:
            filtered_handovers = []
            for record in all_handovers:
                handover_data = record.vital_signs.get("shift_handover", {})
                if handover_data.get("ward") == ward:
                    filtered_handovers.append(record)
                    if len(filtered_handovers) >= limit:
                        break
            handovers = filtered_handovers
            # Adjust total count (approximate)
            total_handovers = len([r for r in all_handovers if r.vital_signs.get("shift_handover", {}).get("ward") == ward])
        else:
            handovers = all_handovers[:limit]
        
        # Format response
        handover_list = []
        for record in handovers:
            handover_data = record.vital_signs.get("shift_handover", {})
            handover_list.append({
                "handover_id": str(record.id),
                "shift_type": handover_data.get("shift_type"),
                "ward": handover_data.get("ward"),
                "patients_count": handover_data.get("patients_count"),
                "created_by": handover_data.get("created_by"),
                "created_at": record.created_at.isoformat()
            })
        
        return {
            "handovers": handover_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_handovers,
                "pages": (total_handovers + limit - 1) // limit
            }
        }

    # ============================================================================
    # WARD MANAGEMENT
    # ============================================================================
    
    async def get_ward_patients(self, ward_name: str, status: Optional[str], current_user: User) -> Dict[str, Any]:
        """Get all patients in a specific ward"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get admissions in this ward
        query = select(Admission).where(
            and_(
                Admission.hospital_id == user_context["hospital_id"],
                Admission.department_id == nurse.department_id,
                Admission.ward == ward_name,
                Admission.is_active == True
            )
        ).options(
            selectinload(Admission.patient).selectinload(PatientProfile.user),
            selectinload(Admission.doctor)
        )
        
        result = await self.db.execute(query)
        admissions = result.scalars().all()
        
        # Format patient list
        patients = []
        for admission in admissions:
            # Get latest vitals
            vitals_result = await self.db.execute(
                select(MedicalRecord.vital_signs, MedicalRecord.created_at)
                .where(MedicalRecord.patient_id == admission.patient_id)
                .order_by(desc(MedicalRecord.created_at))
                .limit(1)
            )
            recent_vitals = vitals_result.first()
            
            patients.append({
                "patient_ref": admission.patient.patient_id,
                "patient_name": f"{admission.patient.user.first_name} {admission.patient.user.last_name}",
                "admission_number": admission.admission_number,
                "room_number": admission.room_number,
                "bed_number": admission.bed_number,
                "admission_date": admission.admission_date.isoformat(),
                "attending_doctor": f"{admission.doctor.first_name} {admission.doctor.last_name}" if admission.doctor else None,
                "latest_vitals": recent_vitals.vital_signs if recent_vitals else {},
                "vitals_recorded_at": recent_vitals.created_at.isoformat() if recent_vitals else None
            })
        
        return {
            "ward_name": ward_name,
            "department": nurse.department.name,
            "patient_count": len(patients),
            "patients": patients
        }

    async def get_wards_overview(self, current_user: User) -> Dict[str, Any]:
        """Get overview of all wards in nurse's department"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get all active admissions in nurse's department
        result = await self.db.execute(
            select(Admission)
            .where(
                and_(
                    Admission.hospital_id == user_context["hospital_id"],
                    Admission.department_id == nurse.department_id,
                    Admission.is_active == True
                )
            )
        )
        
        admissions = result.scalars().all()
        
        # Group by ward
        wards = {}
        for admission in admissions:
            ward = admission.ward or "GENERAL"
            if ward not in wards:
                wards[ward] = {
                    "ward_name": ward,
                    "patient_count": 0,
                    "occupied_beds": []
                }
            
            wards[ward]["patient_count"] += 1
            if admission.bed_number:
                wards[ward]["occupied_beds"].append(admission.bed_number)
        
        # Format response
        wards_list = list(wards.values())
        
        return {
            "department": nurse.department.name,
            "total_wards": len(wards_list),
            "total_patients": sum(w["patient_count"] for w in wards_list),
            "wards": wards_list
        }

    # ============================================================================
    # PATIENT CARE PLANS
    # ============================================================================
    
    async def create_care_plan(self, care_plan_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Create nursing care plan for a patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(care_plan_data["patient_ref"], nurse)
        
        # Create care plan as medical record
        # Note: doctor_id is required by DB constraint, using nurse's user_id as workaround
        care_plan_record = MedicalRecord(
            id=uuid.uuid4(),
            hospital_id=user_context["hospital_id"],
            patient_id=patient.id,
            doctor_id=user_context["user_id"],  # Using nurse's user_id (DB constraint requires non-null)
            chief_complaint="Nursing Care Plan",
            examination_findings=care_plan_data.get("notes", ""),
            vital_signs={
                "care_plan": {
                    "diagnosis": care_plan_data["diagnosis"],
                    "goals": care_plan_data["goals"],
                    "interventions": care_plan_data["interventions"],
                    "expected_outcomes": care_plan_data["expected_outcomes"],
                    "review_date": care_plan_data["review_date"],
                    "created_by": f"{current_user.first_name} {current_user.last_name} (Nurse)",
                    "nurse_id": user_context["user_id"],
                    "status": "ACTIVE"
                }
            },
            is_finalized=True
        )
        
        self.db.add(care_plan_record)
        await self.db.commit()
        
        return {
            "care_plan_id": str(care_plan_record.id),
            "patient_ref": care_plan_data["patient_ref"],
            "diagnosis": care_plan_data["diagnosis"],
            "created_by": f"{current_user.first_name} {current_user.last_name}",
            "created_at": care_plan_record.created_at.isoformat(),
            "message": "Care plan created successfully"
        }

    async def get_patient_care_plans(self, patient_ref: str, active_only: bool, current_user: User) -> Dict[str, Any]:
        """Get care plans for a patient"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get patient with department access check
        patient = await self.get_patient_by_ref_with_department_check(patient_ref, nurse)
        
        # Query care plans
        query = select(MedicalRecord).where(
            and_(
                MedicalRecord.patient_id == patient.id,
                MedicalRecord.chief_complaint == "Nursing Care Plan"
            )
        ).order_by(desc(MedicalRecord.created_at))
        
        # Note: Removed .contains() filter - will filter in Python if needed
        # if active_only:
        #     query = query.where(MedicalRecord.vital_signs.contains({"care_plan": {"status": "ACTIVE"}}))
        
        result = await self.db.execute(query)
        all_care_plans = result.scalars().all()
        
        # Filter by active status in Python if specified
        if active_only:
            care_plans = [
                record for record in all_care_plans
                if record.vital_signs.get("care_plan", {}).get("status") == "ACTIVE"
            ]
        else:
            care_plans = all_care_plans
        
        # Format response
        plans_list = []
        for record in care_plans:
            care_plan = record.vital_signs.get("care_plan", {})
            plans_list.append({
                "care_plan_id": str(record.id),
                "diagnosis": care_plan.get("diagnosis"),
                "goals": care_plan.get("goals", []),
                "interventions": care_plan.get("interventions", []),
                "expected_outcomes": care_plan.get("expected_outcomes", []),
                "review_date": care_plan.get("review_date"),
                "status": care_plan.get("status", "ACTIVE"),
                "created_by": care_plan.get("created_by"),
                "created_at": record.created_at.isoformat(),
                "notes": record.examination_findings
            })
        
        return {
            "patient_ref": patient_ref,
            "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
            "care_plans": plans_list,
            "total_plans": len(plans_list)
        }

    async def update_care_plan(self, care_plan_id: str, care_plan_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """Update existing care plan"""
        user_context = self.get_user_context(current_user)
        nurse = await self.get_nurse_profile(user_context)
        
        # Get care plan record
        result = await self.db.execute(
            select(MedicalRecord)
            .where(
                and_(
                    MedicalRecord.id == care_plan_id,
                    MedicalRecord.hospital_id == user_context["hospital_id"],
                    MedicalRecord.chief_complaint == "Nursing Care Plan"
                )
            )
        )
        
        care_plan_record = result.scalar_one_or_none()
        if not care_plan_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Care plan not found"
            )
        
        # Update care plan data
        existing_care_plan = care_plan_record.vital_signs.get("care_plan", {})
        existing_care_plan.update({
            "diagnosis": care_plan_data["diagnosis"],
            "goals": care_plan_data["goals"],
            "interventions": care_plan_data["interventions"],
            "expected_outcomes": care_plan_data["expected_outcomes"],
            "review_date": care_plan_data["review_date"],
            "updated_by": f"{current_user.first_name} {current_user.last_name} (Nurse)",
            "updated_at": datetime.utcnow().isoformat()
        })
        
        care_plan_record.vital_signs["care_plan"] = existing_care_plan
        care_plan_record.examination_findings = care_plan_data.get("notes", care_plan_record.examination_findings)
        
        await self.db.commit()
        
        return {
            "care_plan_id": care_plan_id,
            "updated_by": f"{current_user.first_name} {current_user.last_name}",
            "updated_at": datetime.utcnow().isoformat(),
            "message": "Care plan updated successfully"
        }
