import frappe


def on_attendance_change(doc, method):
    """
    Fired on Attendance after_insert / on_submit / on_cancel / on_update_after_submit.

    - Draft summary   → re-aggregate in place via db_update (no lifecycle triggers).
    - Submitted summary → add a warning comment; never touch field values.
    - Cancelled summary → skip silently.
    - No summary yet  → skip silently (creation is manual or via bulk page).
    """
    try:
        employee = doc.employee
        attendance_date = doc.attendance_date

        # attendance_date may arrive as a string or a date object
        if hasattr(attendance_date, "year"):
            year = attendance_date.year
            month = attendance_date.month
        else:
            from frappe.utils import getdate
            d = getdate(attendance_date)
            year = d.year
            month = d.month

        summary_name = f"{employee}-{year}-{month:02d}"

        status = frappe.db.get_value(
            "Attendance Summary", summary_name, "docstatus"
        )

        if status is None:
            return  # no summary for this month — nothing to do

        if status == 2:
            return  # cancelled — skip

        if status == 0:
            # Draft: re-aggregate without going through full save lifecycle
            summary = frappe.get_doc("Attendance Summary", summary_name)
            summary.refresh_from_attendance()
            summary.db_update()
            frappe.db.commit()

        elif status == 1:
            # Submitted (locked): leave values alone, just notify
            summary = frappe.get_doc("Attendance Summary", summary_name)
            summary.add_comment(
                "Comment",
                text=(
                    f"⚠️ Underlying attendance for {attendance_date} changed after lock "
                    f"(triggered by {method} on {doc.name}). "
                    "Manual review may be needed."
                ),
            )
            frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"attendance_summary_hooks.on_attendance_change failed "
            f"[{getattr(doc, 'name', '?')}]",
        )
