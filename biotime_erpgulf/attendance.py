import requests
import frappe
from datetime import datetime, timedelta, time
from frappe.utils import get_datetime, now_datetime
import traceback


def checkin_exists(employee, punch_dt):
    start = punch_dt.replace(second=0, microsecond=0)
    end = start + timedelta(minutes=1)
    return frappe.db.exists(
        "Employee Checkin",
        {
            "employee": employee,
            "device_id": "BioTime",
            "time": ["between", [start, end]],
        },
    )


def calculate_attendance(employee, date, punches):
    if not punches:
        return None

    punches = sorted(punches)

    # Define time boundaries
    checkout_start  = punches[0].replace(hour=12, minute=0, second=0, microsecond=0)
    late_start      = punches[0].replace(hour=8,  minute=20, second=0, microsecond=0)
    half_day_start  = punches[0].replace(hour=9,  minute=0,  second=0, microsecond=0)
    absent_start    = punches[0].replace(hour=12, minute=0,  second=0, microsecond=0)
    overtime_start  = punches[0].replace(hour=15, minute=0,  second=0, microsecond=0)

    # First punch = check in
    first_punch = punches[0]

    # Last punch AFTER 12:00 = check out
    out_punches = [p for p in punches if p >= checkout_start]
    last_punch = out_punches[-1] if out_punches else None

    # Determine status from first punch
    status = "Absent"
    late_minutes = 0

    if first_punch < late_start:
        status = "Present"
        late_minutes = 0
    elif first_punch < half_day_start:
        status = "Present"
        diff = first_punch - late_start
        late_minutes = int(diff.total_seconds() / 60)
    elif first_punch < absent_start:
        status = "Half Day"
        late_minutes = 0
    else:
        status = "Absent"
        late_minutes = 0

    # Calculate working hours
    working_hours = 0.0
    if last_punch:
        diff = last_punch - first_punch
        working_hours = round(diff.total_seconds() / 3600, 2)

    # Calculate overtime — must be >= 1 hour to count (HR rule)
    overtime_hours = 0.0
    overtime_amount = 0.0
    if last_punch and last_punch > overtime_start:
        diff = last_punch - overtime_start
        raw_ot = diff.total_seconds() / 3600
        if raw_ot >= 1.0:
            overtime_hours = round(raw_ot, 2)
            overtime_amount = round(overtime_hours * 1.5, 2)

    return {
        "status": status,
        "late_minutes": late_minutes,
        "working_hours": working_hours,
        "overtime_hours": overtime_hours,
        "overtime_amount": overtime_amount,
    }

def process_attendance_for_employee_date(employee, date):
    """Process and save attendance for one employee on one date"""
    # Get all checkins for this employee on this date
    checkins = frappe.db.sql("""
        SELECT time FROM `tabEmployee Checkin`
        WHERE employee = %s
        AND DATE(time) = %s
        ORDER BY time ASC
    """, (employee, date), as_dict=True)

    punch_times = [c.time for c in checkins]

    if not punch_times:
        return

    result = calculate_attendance(employee, date, punch_times)
    if not result:
        return

    company = frappe.db.get_value("Employee", employee, "company")

    # Check if attendance already exists
    existing = frappe.db.get_value("Attendance", {
        "employee": employee,
        "attendance_date": date,
    }, "name")

    if existing:
        # Update existing — cancel, amend, resubmit
        doc = frappe.get_doc("Attendance", existing)
        if doc.docstatus == 1:
            doc.cancel()
            frappe.db.commit()
            doc2 = frappe.copy_doc(doc)
            doc2.docstatus = 0
            doc2.status = result["status"]
            doc2.late_minutes = result["late_minutes"]
            doc2.working_hours = result["working_hours"]
            doc2.overtime_hours = result["overtime_hours"]
            doc2.overtime_amount = result["overtime_amount"]
            doc2.insert(ignore_permissions=True)
            doc2.submit()
        else:
            doc.status = result["status"]
            doc.late_minutes = result["late_minutes"]
            doc.working_hours = result["working_hours"]
            doc.overtime_hours = result["overtime_hours"]
            doc.overtime_amount = result["overtime_amount"]
            doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": date,
            "status": result["status"],
            "shift": "Normal",
            "company": company,
            "late_minutes": result["late_minutes"],
            "working_hours": result["working_hours"],
            "overtime_hours": result["overtime_hours"],
            "overtime_amount": result["overtime_amount"],
        })
        doc.insert(ignore_permissions=True)
        doc.submit()

    frappe.db.commit()


@frappe.whitelist()
def biotime_attendance():
    frappe.enqueue(
        "biotime_erpgulf.attendance.run_biotime_attendance",
        queue="long",
        job_name="BioTime Datetime Sync",
    )
    return {"message": "BioTime sync started"}


def run_biotime_attendance():
    logger = frappe.logger("biotime")

    try:
        settings = frappe.get_single("BioTime Settings")
    except Exception:
        frappe.throw("BioTime Settings DocType not found")

    if not settings.start_year:
        frappe.throw("Start Year is mandatory in BioTime Settings")

    now_dt = now_datetime()

    if settings.last_synced_datetime:
        start_dt = get_datetime(settings.last_synced_datetime)
        if start_dt > now_dt:
            start_dt = now_dt
    else:
        start_dt = datetime(int(settings.start_year), 1, 1)

    end_dt = start_dt + timedelta(days=30)
    if end_dt > now_dt:
        end_dt = now_dt

    logger.info(f"BioTime sync window: {start_dt} → {end_dt}")

    if start_dt >= end_dt:
        return "No new data to sync"

    base_url = settings.biotime_url.rstrip("/") + "/iclock/api/transactions/"
    headers = {"Authorization": f"Token {settings.biotime_token}"}

    inserted = 0
    skipped = 0
    page = 1
    affected_dates = set()  # track which employee+date combos need reprocessing

    while True:
        try:
            response = requests.get(
                base_url,
                headers=headers,
                params={
                    "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "page": page,
                },
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("data") or []

        except Exception:
            logger.exception("BioTime API failed")
            break

        if not rows:
            break

        for row in rows:
            try:
                emp_code = row.get("emp_code")
                punch_time = row.get("punch_time")
                punch_state = row.get("punch_state_display")
                area_alias = row.get("area_alias") or None

                if not (emp_code and punch_time):
                    skipped += 1
                    continue

                punch_dt = get_datetime(punch_time)

                employee = frappe.db.get_value(
                    "Employee",
                    {"biotime_emp_code": emp_code},
                    "name",
                )

                if not employee:
                    skipped += 1
                    continue

                if checkin_exists(employee, punch_dt):
                    skipped += 1
                    continue

                # Determine log type
                # Force IN before 12:00 and OUT after 12:00
                if punch_dt.hour < 12:
                    log_type = "IN"
                else:
                    log_type = "OUT"

                frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": employee,
                    "time": punch_dt,
                    "log_type": log_type,
                    "device_id": "BioTime",
                    "shift": "Normal",
                    "custom_location_id": area_alias,
                }).insert(ignore_permissions=True)

                inserted += 1
                affected_dates.add((employee, str(punch_dt.date())))

            except frappe.UniqueValidationError:
                skipped += 1
            except Exception:
                logger.exception("Row insert failed")
                skipped += 1

        if payload.get("next"):
            page += 1
        else:
            break

    # Reprocess attendance for all affected employee+date combos
    logger.info(f"Reprocessing attendance for {len(affected_dates)} employee-date pairs")
    for employee, date in affected_dates:
        try:
            process_attendance_for_employee_date(employee, date)
        except Exception:
            logger.exception(f"Attendance processing failed for {employee} on {date}")

    frappe.db.set_value(
        "BioTime Settings",
        None,
        "last_synced_datetime",
        end_dt,
    )
    frappe.db.commit()

    logger.info(f"BioTime sync done. Inserted={inserted}, Skipped={skipped}")
    return f"Inserted={inserted}, Skipped={skipped}"


@frappe.whitelist()
def add_manual_punch(employee, date, punch_time, log_type):
    """
    Manually add a punch for an employee and reprocess their attendance
    """
    if not (employee and date and punch_time and log_type):
        frappe.throw("All fields are required")

    # Validate employee exists
    if not frappe.db.exists("Employee", employee):
        frappe.throw(f"Employee {employee} not found")

    punch_dt = get_datetime(f"{date} {punch_time}")

    # Check duplicate
    if checkin_exists(employee, punch_dt):
        frappe.throw("A punch already exists within the same minute")

    # Insert checkin
    doc = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee,
        "time": punch_dt,
        "log_type": log_type,
        "device_id": "Manual",
        "shift": "Normal",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    # Reprocess attendance for this employee on this date
    process_attendance_for_employee_date(employee, date)

    return {
        "message": f"✅ Punch added and attendance updated for {employee} on {date}"
    }
