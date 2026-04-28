import frappe


def run():
    settings = frappe.get_single("BioTime Settings")
    if not settings.start_year:
        settings.start_year = 2026
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"start_year set to {settings.start_year}")
    else:
        print(f"start_year already set to {settings.start_year} — no change")
