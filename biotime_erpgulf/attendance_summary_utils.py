import frappe


@frappe.whitelist()
def bulk_create_summaries(year, month, company=None):
    """
    Create draft Attendance Summary records for all active employees
    for the given (year, month).

    Skips employees that already have a non-cancelled summary.
    Each new record auto-aggregates via before_save → refresh_from_attendance().

    Returns:
        {
            "summary": {"created": N, "existed": M, "failed": K, "total": T},
            "details": [{"employee": ..., "status": ..., "message": ...}, ...]
        }
    """
    year = int(year)
    month = str(month).zfill(2)

    filters = {"status": "Active"}
    if company:
        filters["company"] = company

    employees = frappe.get_all("Employee", filters=filters, pluck="name")

    results = []
    for emp in employees:
        try:
            expected_name = f"{emp}-{year}-{month}"
            existing_status = frappe.db.get_value(
                "Attendance Summary", expected_name, "docstatus"
            )

            if existing_status is not None and existing_status != 2:
                label = ["Draft", "Submitted"][int(existing_status)] if existing_status in (0, 1) else "Unknown"
                results.append({
                    "employee": emp,
                    "status": "Existed",
                    "message": f"Summary already exists ({label})",
                })
                continue

            doc = frappe.get_doc({
                "doctype": "Attendance Summary",
                "employee": emp,
                "year": year,
                "month": month,
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()  # per-insert commit keeps cache consistent for the next iteration
            results.append({
                "employee": emp,
                "status": "Created",
                "message": f"Created {doc.name}",
            })

        except frappe.exceptions.DuplicateEntryError:
            # Cache miss on the existence check — record was already there
            results.append({
                "employee": emp,
                "status": "Existed",
                "message": "Summary already exists",
            })
        except Exception:
            results.append({
                "employee": emp,
                "status": "Failed",
                "message": frappe.get_traceback().strip().splitlines()[-1][:200],
            })
            frappe.log_error(
                frappe.get_traceback(),
                f"bulk_create_summaries: failed for {emp}",
            )

    created = sum(1 for r in results if r["status"] == "Created")
    existed = sum(1 for r in results if r["status"] == "Existed")
    failed = sum(1 for r in results if r["status"] == "Failed")

    return {
        "summary": {
            "created": created,
            "existed": existed,
            "failed": failed,
            "total": len(results),
        },
        "details": results,
    }
