from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

from biotime_erpgulf.payroll_utils import (
    get_absent_days,
    get_total_late_minutes,
    get_total_overtime_amount,
)


class CustomSalarySlip(SalarySlip):
    """Extends SalarySlip to make biotime_erpgulf payroll helpers available
    inside Salary Component formula expressions without dotted module paths.

    Formulas can call:
        get_total_late_minutes(employee, start_date, end_date)
        get_total_overtime_amount(employee, start_date, end_date)
        get_absent_days(employee, start_date, end_date)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whitelisted_globals.update(
            {
                "get_total_late_minutes": get_total_late_minutes,
                "get_total_overtime_amount": get_total_overtime_amount,
                "get_absent_days": get_absent_days,
            }
        )

    def autoname(self):
        # HRMS's __init__ sets default_series before self.employee is populated,
        # which produces 'Sal Slip/None/...' names. Recompute now that self.employee is set.
        if self.employee:
            self.default_series = f"Sal Slip/{self.employee}/.#####"
        super().autoname()
