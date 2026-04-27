"""
Payroll helpers for biotime_erpgulf.

These functions are called from Salary Structure formulas. ERPNext passes
`employee`, `start_date`, `end_date` as formula variables automatically when
generating a Salary Slip.

Data source: Attendance Summary (docstatus = 1, i.e. submitted only).
If no submitted summary exists for the period, an error is raised so HR
knows payroll is missing data and must lock the summary first.
"""

import frappe
from frappe import _


def _get_summary_field(employee, start_date, end_date, fieldname):
    """
    Look up the value of `fieldname` from a SUBMITTED Attendance Summary
    for this employee and date range. Raises a clear error if missing.
    """
    value = frappe.db.get_value(
        "Attendance Summary",
        {
            "employee": employee,
            "from_date": start_date,
            "to_date": end_date,
            "docstatus": 1,
        },
        fieldname,
    )
    if value is None:
        frappe.throw(
            _(
                "No submitted Attendance Summary found for employee {0} "
                "for the period {1} to {2}. Please create and submit the "
                "summary before running payroll."
            ).format(employee, start_date, end_date),
            title=_("Missing Attendance Summary"),
        )
    return value


def get_total_late_minutes(employee, start_date, end_date):
    """Total late minutes for the period (already grace-adjusted in attendance)."""
    return int(_get_summary_field(employee, start_date, end_date, "total_late_minutes") or 0)


def get_total_overtime_amount(employee, start_date, end_date):
    """
    Total overtime amount in 'hours-equivalent' form (raw OT × 1.5).
    This is the value to multiply by hourly_rate to get OT pay.
    The 1-hour-per-day threshold is applied at the attendance level, not here.
    """
    return float(_get_summary_field(employee, start_date, end_date, "total_overtime_amount") or 0)


def get_absent_days(employee, start_date, end_date):
    """Number of days marked Absent in the period."""
    return int(_get_summary_field(employee, start_date, end_date, "absent_days") or 0)


def get_half_days(employee, start_date, end_date):
    """
    Number of Half Day records in the period.
    NOTE: Returns 0 — Attendance Summary does not yet store half_days (deferred
    until the custom leave DocType is built). Kept as a placeholder so existing
    Salary Structure formulas that call this don't break.
    """
    return 0
