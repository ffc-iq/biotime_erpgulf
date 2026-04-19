"""
Payroll helpers for biotime_erpgulf.

These functions are called from Salary Structure formulas.
ERPNext passes `employee`, `start_date`, `end_date` as formula variables
automatically when generating a Salary Slip, so no extra wiring needed.
"""

import frappe


def get_total_late_minutes(employee, start_date, end_date):
    """
    Sum the custom `late_minutes` field from submitted Attendance records
    for the given employee and date range.

    Returns 0 if no records found (so the formula never breaks).
    """
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(late_minutes), 0) AS total
        FROM `tabAttendance`
        WHERE employee = %s
          AND attendance_date BETWEEN %s AND %s
          AND docstatus = 1
    """, (employee, start_date, end_date), as_dict=True)
    return float(result[0].total or 0)


def get_total_overtime_amount(employee, start_date, end_date):
    """
    Sum the custom `overtime_amount` field from submitted Attendance records.
    Note: overtime_amount is already (overtime_hours * 1.5), so this value
    represents the 'hours equivalent' to pay at the normal hourly rate.
    """
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(overtime_amount), 0) AS total
        FROM `tabAttendance`
        WHERE employee = %s
          AND attendance_date BETWEEN %s AND %s
          AND docstatus = 1
    """, (employee, start_date, end_date), as_dict=True)
    return float(result[0].total or 0)


def get_absent_days(employee, start_date, end_date):
    """
    Count days marked as 'Absent' in the period.
    """
    result = frappe.db.sql("""
        SELECT COUNT(*) AS cnt
        FROM `tabAttendance`
        WHERE employee = %s
          AND attendance_date BETWEEN %s AND %s
          AND status = 'Absent'
          AND docstatus = 1
    """, (employee, start_date, end_date), as_dict=True)
    return int(result[0].cnt or 0)


def get_half_days(employee, start_date, end_date):
    """
    Count days marked as 'Half Day' in the period.
    """
    result = frappe.db.sql("""
        SELECT COUNT(*) AS cnt
        FROM `tabAttendance`
        WHERE employee = %s
          AND attendance_date BETWEEN %s AND %s
          AND status = 'Half Day'
          AND docstatus = 1
    """, (employee, start_date, end_date), as_dict=True)
    return int(result[0].cnt or 0)
