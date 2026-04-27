import calendar

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, today


class AttendanceSummary(Document):
    def validate(self):
        self._set_dates()
        self._check_duplicate()

    def before_save(self):
        if self.docstatus == 0:
            self.refresh_from_attendance()

    def before_submit(self):
        if getdate(self.to_date) >= getdate(today()):
            frappe.msgprint(
                "This month is still in progress — the summary may be incomplete.",
                indicator="yellow",
                title="Month in Progress",
            )

    def _set_dates(self):
        year = int(self.year)
        month = int(self.month)
        self.from_date = f"{year:04d}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        self.to_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    def _check_duplicate(self):
        existing = frappe.db.get_value(
            "Attendance Summary",
            {
                "employee": self.employee,
                "year": self.year,
                "month": self.month,
                "docstatus": ["!=", 2],
                "name": ["!=", self.name or ""],
            },
            "name",
        )
        if existing:
            frappe.throw(
                f"An Attendance Summary already exists for {self.employee} "
                f"— {self.year}-{self.month}: "
                f'<a href="/app/attendance-summary/{existing}">{existing}</a>',
                title="Duplicate Summary",
            )

    def refresh_from_attendance(self):
        if not (self.from_date and self.to_date):
            self._set_dates()

        result = frappe.db.sql(
            """
            SELECT
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END)  AS present_days,
                SUM(CASE WHEN status = 'Absent'  THEN 1 ELSE 0 END)  AS absent_days,
                COALESCE(SUM(working_hours),   0)                     AS total_working_hours,
                COALESCE(SUM(late_minutes),    0)                     AS total_late_minutes,
                COALESCE(SUM(overtime_hours),  0)                     AS total_overtime_hours,
                COALESCE(SUM(overtime_amount), 0)                     AS total_overtime_amount
            FROM `tabAttendance`
            WHERE employee          = %s
              AND attendance_date  BETWEEN %s AND %s
              AND docstatus        = 1
            """,
            (self.employee, self.from_date, self.to_date),
            as_dict=True,
        )

        if result:
            row = result[0]
            self.present_days = int(row.present_days or 0)
            self.absent_days = int(row.absent_days or 0)
            self.total_working_hours = round(float(row.total_working_hours or 0), 2)
            self.total_late_minutes = int(row.total_late_minutes or 0)
            self.total_overtime_hours = round(float(row.total_overtime_hours or 0), 2)
            self.total_overtime_amount = round(float(row.total_overtime_amount or 0), 2)

        self.last_refreshed_on = now_datetime()

    @frappe.whitelist()
    def refresh(self):
        """Called by the manual Refresh button — draft only."""
        if self.docstatus != 0:
            frappe.throw("Can only refresh a Draft summary.")
        self.refresh_from_attendance()
        self.save(ignore_permissions=True)
        return {"message": "Refreshed successfully"}
