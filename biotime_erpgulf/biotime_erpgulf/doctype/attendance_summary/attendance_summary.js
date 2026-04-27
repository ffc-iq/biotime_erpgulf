frappe.ui.form.on("Attendance Summary", {
	refresh(frm) {
		// "Month in progress" banner when to_date is today or in the future
		if (frm.doc.to_date) {
			const today = frappe.datetime.get_today();
			if (frm.doc.to_date >= today) {
				frm.dashboard.add_comment(
					"⏳ Month in progress — data may be incomplete.",
					"yellow",
					true
				);
			}
		}

		// Manual refresh button — draft only
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Refresh from Attendance"), () => {
				frappe.call({
					method: "refresh",
					doc: frm.doc,
					freeze: true,
					freeze_message: __("Refreshing…"),
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
							frappe.show_alert({ message: __("Refreshed"), indicator: "green" });
						}
					},
				});
			});
		}
	},
});
