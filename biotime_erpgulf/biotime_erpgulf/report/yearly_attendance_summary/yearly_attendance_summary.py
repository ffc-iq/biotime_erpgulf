import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """
    One row per employee. Columns:
      Employee | Employee Name | Company | Year |
      Jan_Late | Jan_OT | ... | Dec_Late | Dec_OT |
      YTD_Late | YTD_OT | YTD_Absent
    """
    cols = [
        {"label": _("Employee"),      "fieldname": "employee",      "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": _("Company"),       "fieldname": "company",       "fieldtype": "Link", "options": "Company",  "width": 140},
        {"label": _("Year"),          "fieldname": "year",          "fieldtype": "Int",  "width": 70},
    ]

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i, m in enumerate(month_names, 1):
        cols.append({
            "label": _(f"{m} Late (min)"),
            "fieldname": f"m{i:02d}_late",
            "fieldtype": "Int",
            "width": 90,
        })
        cols.append({
            "label": _(f"{m} OT"),
            "fieldname": f"m{i:02d}_ot",
            "fieldtype": "Float",
            "precision": 2,
            "width": 80,
        })

    cols.extend([
        {"label": _("YTD Late (min)"),    "fieldname": "ytd_late",   "fieldtype": "Int",   "width": 110},
        {"label": _("YTD OT"),            "fieldname": "ytd_ot",     "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": _("YTD Absent (days)"), "fieldname": "ytd_absent", "fieldtype": "Int",   "width": 120},
    ])
    return cols


def get_data(filters):
    conditions = ["s.docstatus != 2"]
    params = {}

    year = filters.get("year") or frappe.utils.now_datetime().year
    conditions.append("s.year = %(year)s")
    params["year"] = int(year)

    if filters.get("employee"):
        conditions.append("s.employee = %(employee)s")
        params["employee"] = filters["employee"]

    if filters.get("company"):
        conditions.append("s.company = %(company)s")
        params["company"] = filters["company"]

    where_clause = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            s.employee,
            s.employee_name,
            s.company,
            s.year,
            s.month,
            s.total_late_minutes,
            s.total_overtime_amount,
            s.absent_days
        FROM `tabAttendance Summary` s
        WHERE {where_clause}
        ORDER BY s.employee, s.month
        """,
        params,
        as_dict=True,
    )

    # Pivot: one dict per employee, filled month-by-month
    pivoted = {}
    for r in rows:
        key = r.employee
        if key not in pivoted:
            pivoted[key] = {
                "employee": r.employee,
                "employee_name": r.employee_name,
                "company": r.company,
                "year": r.year,
                "ytd_late": 0,
                "ytd_ot": 0.0,
                "ytd_absent": 0,
            }
        month_num = int(r.month)
        late = int(r.total_late_minutes or 0)
        ot = float(r.total_overtime_amount or 0)
        absent = int(r.absent_days or 0)

        pivoted[key][f"m{month_num:02d}_late"] = late
        pivoted[key][f"m{month_num:02d}_ot"] = ot
        pivoted[key]["ytd_late"] += late
        pivoted[key]["ytd_ot"] += ot
        pivoted[key]["ytd_absent"] += absent

    for row in pivoted.values():
        row["ytd_ot"] = round(row["ytd_ot"], 2)

    return sorted(pivoted.values(), key=lambda x: x["employee"])
