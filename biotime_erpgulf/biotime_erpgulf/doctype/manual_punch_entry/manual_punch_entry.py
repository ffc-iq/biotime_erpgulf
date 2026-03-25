import frappe
from frappe.model.document import Document
from biotime_erpgulf.attendance import add_manual_punch

class ManualPunchEntry(Document):
    def on_submit(self):
        # Call our existing logic when this form is submitted
        # Ensure time is a string format
        time_str = str(self.time)
        if len(time_str) == 5: # If format is HH:MM, append seconds
            time_str += ":00"
            
        result = add_manual_punch(self.employee, self.date, time_str, self.log_type)
        frappe.msgprint(result.get("message"))