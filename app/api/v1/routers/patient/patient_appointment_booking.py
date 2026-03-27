"""
Patient Appointment Booking API
Authenticated appointment booking system for registered patients.
PATIENT AUTHENTICATION REQUIRED: Patients must login to book appointments.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.core.database import get_db_session
from app.models.hospital import Department
from app.models.patient import PatientProfile, Appointment
from app.models.user import User
from app.core.enums import AppointmentStatus, UserRole, UserStatus
from app.core.utils import generate_appointment_ref
from app.core.security import get_current_user
from app.schemas.patient_care import AppointmentBookingCreate, AppointmentCancellationCreate

router = APIRouter(prefix="/patient-appointment-booking", tags=["Patient Portal - Appointment Booking"])


async def get_current_patient(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> PatientProfile:
    """
    Get current authenticated patient.
    Ensures only patients can access appointment booking endpoints.
    """
    # Check if user has PATIENT role
    user_roles = [role.name for role in current_user.roles] if current_user.roles else []
    if UserRole.PATIENT not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INSUFFICIENT_PERMISSIONS",
                "message": "Only patients can access appointment booking. Please login with patient credentials."
            }
        )
    
    # Get patient profile
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PATIENT_PROFILE_NOT_FOUND",
                "message": "Patient profile not found. Please contact support."
            }
        )
    
    return patient


# ============================================================================
# AUTHENTICATED ENDPOINTS (Patient Authentication Required)
# Patient's hospital_id is used (assigned at registration); no need to ask for hospital.
# ============================================================================

async def _get_patient_hospital(
    current_patient: PatientProfile, db: AsyncSession
):
    """Get hospital for current patient. Raises 400 if patient has no hospital_id (must register to a hospital first)."""
    from app.models.tenant import Hospital
    if not current_patient.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient must be registered to a hospital to book appointments. Please complete registration with a hospital."
        )
    result = await db.execute(
        select(Hospital).where(
            and_(
                Hospital.id == current_patient.hospital_id,
                Hospital.is_active == True
            )
        )
    )
    hospital = result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your registered hospital is not found or inactive"
        )
    return hospital


@router.get("/departments")
async def get_departments(
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get list of departments in the patient's hospital.
    
    Access Control:
    - **Who can access:** Patients only (own hospital from JWT token)
    """
    hospital = await _get_patient_hospital(current_patient, db)
    query = select(Department).where(
        and_(
            Department.hospital_id == hospital.id,
            Department.is_active == True
        )
    ).order_by(Department.name)
    result = await db.execute(query)
    departments = result.scalars().all()
    return [
        {
            "name": dept.name,
            "description": dept.description,
            "code": dept.code,
            "location": dept.location,
            "is_emergency": dept.is_emergency,
            "is_24x7": dept.is_24x7,
            "hospital_name": hospital.name,
        }
        for dept in departments
    ]


@router.get("/departments/{department_name}/doctors")
async def get_department_doctors(
    department_name: str,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get doctors by department name in the patient's hospital.
    
    Access Control:
    - **Who can access:** Patients only (own hospital from JWT token)
    """
    hospital = await _get_patient_hospital(current_patient, db)
    dept_query = select(Department).where(
        and_(
            Department.hospital_id == hospital.id,
            Department.name.ilike(f"%{department_name}%"),
            Department.is_active == True
        )
    )
    dept_result = await db.execute(dept_query)
    department = dept_result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{department_name}' not found in your hospital"
        )
    
    # Get doctors in the department (from staff assignments)
    from app.models.hospital import StaffDepartmentAssignment
    from app.models.user import Role
    
    result = await db.execute(
        select(StaffDepartmentAssignment)
        .join(User, StaffDepartmentAssignment.staff_id == User.id)
        .join(User.roles)
        .where(
            and_(
                StaffDepartmentAssignment.department_id == department.id,
                StaffDepartmentAssignment.is_active == True,
                User.status == UserStatus.ACTIVE,
                Role.name == UserRole.DOCTOR  # Only get doctors
            )
        )
        .options(selectinload(StaffDepartmentAssignment.staff))
        .order_by(User.first_name)
    )
    
    assignments = result.scalars().all()
    
    # Convert staff assignments to doctor list
    doctors = []
    for assignment in assignments:
        staff = assignment.staff
        doctors.append({
            "name": f"Dr. {staff.first_name} {staff.last_name}",
            "specialization": "General Medicine",  # Default since we don't have DoctorProfile
            "designation": "Doctor",  # Default since we don't have DoctorProfile
            "consultation_fee": 500.0,  # Default consultation fee
            "experience_years": 5  # Default experience
        })
    
    return {
        "department_name": department.name,
        "department_code": department.code,
        "hospital_name": hospital.name,
        "doctors": doctors
    }


@router.get("/doctors/{doctor_name}/available-slots")
async def get_doctor_available_slots(
    doctor_name: str,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get available time slots by doctor name in the patient's hospital.
    
    Access Control:
    - **Who can access:** Patients only (own hospital from JWT token)
    """
    from app.models.hospital import StaffDepartmentAssignment
    from app.models.user import Role
    
    hospital = await _get_patient_hospital(current_patient, db)
    doctor_query = select(User).join(
        StaffDepartmentAssignment, User.id == StaffDepartmentAssignment.staff_id
    ).join(User.roles).where(
        and_(
            User.hospital_id == hospital.id,
            or_(
                func.concat('Dr. ', User.first_name, ' ', User.last_name).ilike(f"%{doctor_name}%"),
                func.concat(User.first_name, ' ', User.last_name).ilike(f"%{doctor_name}%")
            ),
            StaffDepartmentAssignment.is_active == True,
            User.status == UserStatus.ACTIVE,
            Role.name == UserRole.DOCTOR
        )
    )
    
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor '{doctor_name}' not found in your hospital"
        )
    
    # Parse date and get day of week
    try:
        appointment_date = datetime.fromisoformat(date)
        day_of_week = appointment_date.strftime('%A').upper()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Since we don't have doctor schedules, create default availability
    # Generate basic time slots from 9 AM to 5 PM (every 30 minutes)
    slots = []
    start_time = datetime.combine(appointment_date.date(), datetime.strptime("09:00", "%H:%M").time())
    end_time = datetime.combine(appointment_date.date(), datetime.strptime("17:00", "%H:%M").time())
    current_time = start_time
    
    while current_time < end_time:
        # Skip lunch break (12:00 - 13:00)
        if current_time.time() >= datetime.strptime("12:00", "%H:%M").time() and current_time.time() < datetime.strptime("13:00", "%H:%M").time():
            current_time += timedelta(minutes=30)
            continue
        
        # Skip past times for today
        if appointment_date.date() == datetime.now().date() and current_time <= datetime.now():
            current_time += timedelta(minutes=30)
            continue
        
        # Check if slot is already booked
        existing_appointment = await db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.doctor_id == doctor.id,
                    Appointment.appointment_date == date,
                    Appointment.appointment_time == current_time.strftime('%H:%M:%S'),
                    Appointment.status.in_([AppointmentStatus.REQUESTED, AppointmentStatus.CONFIRMED])
                )
            )
        )
        
        is_available = existing_appointment.scalar_one_or_none() is None
        
        slots.append({
            "time": current_time.strftime('%H:%M'),
            "is_available": is_available
        })
        
        current_time += timedelta(minutes=30)
    
    return {
        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
        "hospital_name": hospital.name,
        "date": date,
        "available_slots": slots
    }


@router.post("/book-appointment")
async def book_appointment(
    booking_request: AppointmentBookingCreate,
    current_patient: PatientProfile = Depends(get_current_patient),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Book an appointment for authenticated patient.
    
    Access Control:
    - **Who can access:** Patients only (identity from JWT token)
    """
    from app.models.hospital import StaffDepartmentAssignment
    from app.models.user import Role
    
    data = booking_request.dict()
    
    # Validate appointment date/time
    try:
        appointment_datetime = datetime.fromisoformat(f"{data['appointment_date']}T{data['appointment_time']}")
        if appointment_datetime <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book appointments in the past"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date/time format"
        )
    
    # Use patient's hospital (assigned at registration)
    hospital = await _get_patient_hospital(current_patient, db)
    
    # Find department by name in specified hospital
    dept_result = await db.execute(
        select(Department)
        .where(
            and_(
                Department.hospital_id == hospital.id,
                Department.name.ilike(f"%{data['department_name']}%"),
                Department.is_active == True
            )
        )
    )
    
    department = dept_result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{data['department_name']}' not found in {hospital.name}"
        )
    
    # Find doctor by name (from staff assignments in specified hospital)
    doctor_result = await db.execute(
        select(User)
        .join(StaffDepartmentAssignment, User.id == StaffDepartmentAssignment.staff_id)
        .join(User.roles)
        .where(
            and_(
                User.hospital_id == hospital.id,
                StaffDepartmentAssignment.department_id == department.id,
                StaffDepartmentAssignment.is_active == True,
                or_(
                    func.concat('Dr. ', User.first_name, ' ', User.last_name).ilike(f"%{data['doctor_name']}%"),
                    func.concat(User.first_name, ' ', User.last_name).ilike(f"%{data['doctor_name']}%")
                ),
                Role.name == UserRole.DOCTOR,
                User.status == UserStatus.ACTIVE
            )
        )
    )
    
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor '{data['doctor_name']}' not found in {data['department_name']} department at {hospital.name}"
        )
    
    # Check if time slot is available
    existing_appointment = await db.execute(
        select(Appointment)
        .where(
            and_(
                Appointment.doctor_id == doctor.id,
                Appointment.appointment_date == data['appointment_date'],
                Appointment.appointment_time == f"{data['appointment_time']}:00",
                Appointment.status.in_([AppointmentStatus.REQUESTED, AppointmentStatus.CONFIRMED])
            )
        )
    )
    
    if existing_appointment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot is not available"
        )
    
    # Generate appointment reference
    appointment_ref = generate_appointment_ref()
    
    # Ensure appointment_ref is unique
    while True:
        existing_ref = await db.execute(
            select(Appointment).where(Appointment.appointment_ref == appointment_ref)
        )
        if not existing_ref.scalar_one_or_none():
            break
        appointment_ref = generate_appointment_ref()
    
    # Automatically assign hospital_id to patient and user if it's null
    # This links the patient to the hospital when they book their first appointment
    if current_patient.hospital_id is None:
        current_patient.hospital_id = hospital.id
    
    # Also update the user's hospital_id if it's null
    if current_user.hospital_id is None:
        current_user.hospital_id = hospital.id
    
    # Create appointment
    appointment = Appointment(
        appointment_ref=appointment_ref,
        patient_id=current_patient.id,
        doctor_id=doctor.id,
        department_id=department.id,
        hospital_id=hospital.id,  # Use the specified hospital
        appointment_date=data['appointment_date'],
        appointment_time=f"{data['appointment_time']}:00",
        duration_minutes=30,
        status=AppointmentStatus.REQUESTED,
        chief_complaint=data['chief_complaint'],
        consultation_fee=500.0,  # Default consultation fee
        created_by_role=UserRole.PATIENT,
        created_by_user=current_patient.user_id
    )
    
    db.add(appointment)
    await db.commit()
    
    return {
        "success": True,
        "message": "Appointment booked successfully!",
        "patient_ref": current_patient.patient_id,
        "patient_name": f"{current_patient.user.first_name} {current_patient.user.last_name}",
        "appointment_ref": appointment_ref,
        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
        "department_name": department.name,
        "hospital_name": hospital.name,
        "appointment_date": data['appointment_date'],
        "appointment_time": data['appointment_time'],
        "status": AppointmentStatus.REQUESTED,
        "consultation_fee": 500.0
    }


@router.get("/appointment/{appointment_ref}")
async def get_appointment_details(
    appointment_ref: str,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get appointment details by appointment reference.
    
    Access Control:
    - **Who can access:** Patients only (own appointments from JWT token)
    """
    result = await db.execute(
        select(Appointment)
        .where(
            and_(
                Appointment.appointment_ref == appointment_ref,
                Appointment.patient_id == current_patient.id  # Ensure patient can only see their own appointments
            )
        )
        .options(
            selectinload(Appointment.patient).selectinload(PatientProfile.user),
            selectinload(Appointment.doctor),
            selectinload(Appointment.department)
        )
    )
    
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or you don't have permission to view it"
        )
    
    return {
        "appointment_ref": appointment.appointment_ref,
        "patient_ref": appointment.patient.patient_id,
        "patient_name": f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}",
        "patient_phone": appointment.patient.user.phone,
        "patient_email": appointment.patient.user.email,
        "doctor_name": f"Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}",
        "department_name": appointment.department.name,
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.appointment_time,
        "status": appointment.status,
        "chief_complaint": appointment.chief_complaint,
        "consultation_fee": float(appointment.consultation_fee),
        "created_at": appointment.created_at.isoformat(),
        "notes": appointment.notes
    }


@router.get("/my-appointments")
async def get_my_appointments(
    current_patient: PatientProfile = Depends(get_current_patient),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by appointment status"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all appointments for the authenticated patient.
    
    Access Control:
    - **Who can access:** Patients only (own appointments from JWT token)
    """
    offset = (page - 1) * limit
    
    # Build query for patient's appointments only
    query = select(Appointment).where(
        Appointment.patient_id == current_patient.id
    ).options(
        selectinload(Appointment.doctor),
        selectinload(Appointment.department)
    )
    
    # Apply status filter if provided
    if status_filter:
        query = query.where(Appointment.status == status_filter)
    
    # Get total count
    count_query = select(func.count(Appointment.id)).where(
        Appointment.patient_id == current_patient.id
    )
    if status_filter:
        count_query = count_query.where(Appointment.status == status_filter)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset(offset).limit(limit).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    return {
        "appointments": [
            {
                "appointment_ref": apt.appointment_ref,
                "doctor_name": f"Dr. {apt.doctor.first_name} {apt.doctor.last_name}",
                "department_name": apt.department.name,
                "appointment_date": apt.appointment_date,
                "appointment_time": apt.appointment_time,
                "status": apt.status,
                "chief_complaint": apt.chief_complaint,
                "consultation_fee": float(apt.consultation_fee),
                "created_at": apt.created_at.isoformat()
            }
            for apt in appointments
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.patch("/appointment/{appointment_ref}/cancel")
async def cancel_appointment(
    appointment_ref: str,
    cancellation_request: AppointmentCancellationCreate,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cancel an appointment by appointment reference.
    
    Access Control:
    - **Who can access:** Patients only (own appointments from JWT token)
    """
    result = await db.execute(
        select(Appointment)
        .where(
            and_(
                Appointment.appointment_ref == appointment_ref,
                Appointment.patient_id == current_patient.id  # Ensure patient can only cancel their own appointments
            )
        )
    )
    
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or you don't have permission to cancel it"
        )
    
    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status: {appointment.status}"
        )
    
    # Update appointment
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = cancellation_request.cancellation_reason
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Appointment {appointment_ref} has been cancelled successfully",
        "appointment_ref": appointment_ref,
        "status": AppointmentStatus.CANCELLED,
        "cancelled_at": appointment.cancelled_at.isoformat()
    }