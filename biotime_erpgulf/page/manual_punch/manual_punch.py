import frappe

@frappe.whitelist()
def get_employees():
    return frappe.db.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name"],
        order_by="employee_name asc"
    )
