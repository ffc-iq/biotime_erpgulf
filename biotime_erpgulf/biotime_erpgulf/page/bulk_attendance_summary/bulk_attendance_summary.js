frappe.pages["bulk-attendance-summary"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Bulk Attendance Summary Generator",
		single_column: true,
	});

	// ── Filter fields ──────────────────────────────────────────────
	const now = new Date();
	const current_year = now.getFullYear();
	const current_month = String(now.getMonth() + 1).padStart(2, "0");

	const year_field = page.add_field({
		fieldname: "year",
		label: "Year",
		fieldtype: "Int",
		reqd: 1,
		change() { /* no-op */ },
	});
	year_field.set_value(current_year);

	const month_field = page.add_field({
		fieldname: "month",
		label: "Month",
		fieldtype: "Select",
		options: "01\n02\n03\n04\n05\n06\n07\n08\n09\n10\n11\n12",
		reqd: 1,
		change() { /* no-op */ },
	});
	month_field.set_value(current_month);

	const company_field = page.add_field({
		fieldname: "company",
		label: "Company",
		fieldtype: "Link",
		options: "Company",
		change() { /* no-op */ },
	});

	// ── Results container ──────────────────────────────────────────
	const $body = $(wrapper).find(".layout-main-section");
	const $results = $('<div class="bulk-summary-results" style="padding: 15px 20px;"></div>')
		.appendTo($body);

	// ── Primary action ─────────────────────────────────────────────
	page.set_primary_action(
		__("Generate Summaries for All Active Employees"),
		function () {
			const year = year_field.get_value();
			const month = month_field.get_value();
			const company = company_field.get_value();

			if (!year || !month) {
				frappe.msgprint(__("Year and Month are required."));
				return;
			}

			page.btn_primary
				.prop("disabled", true)
				.html('<i class="fa fa-spinner fa-spin"></i> ' + __("Working…"));
			$results.html(
				'<p class="text-muted"><i class="fa fa-spinner fa-spin"></i> ' +
				__("Generating summaries, please wait…") + "</p>"
			);

			frappe.call({
				method: "biotime_erpgulf.attendance_summary_utils.bulk_create_summaries",
				args: { year, month, company: company || null },
				callback(r) {
					page.btn_primary
						.prop("disabled", false)
						.text(__("Generate Summaries for All Active Employees"));

					if (r.exc || !r.message) return;

					const { summary, details } = r.message;

					const badge = (status) => {
						const map = {
							Created: "success",
							Existed: "warning",
							Failed: "danger",
						};
						return `<span class="badge badge-${map[status] || 'secondary'}">${status}</span>`;
					};

					const rows = details
						.map(
							(d) => `
						<tr>
							<td>${frappe.utils.escape_html(d.employee)}</td>
							<td>${badge(d.status)}</td>
							<td>${frappe.utils.escape_html(d.message)}</td>
						</tr>`
						)
						.join("");

					$results.html(`
						<div class="alert alert-info" style="margin-bottom: 15px;">
							<strong>${__("Done")}:</strong>
							${__("Created")} <strong>${summary.created}</strong> &nbsp;·&nbsp;
							${__("Existed")} <strong>${summary.existed}</strong> &nbsp;·&nbsp;
							${__("Failed")} <strong>${summary.failed}</strong> &nbsp;/&nbsp;
							${__("Total")} <strong>${summary.total}</strong>
						</div>
						<table class="table table-bordered table-sm" style="background: white;">
							<thead class="thead-light">
								<tr>
									<th>${__("Employee")}</th>
									<th>${__("Status")}</th>
									<th>${__("Message")}</th>
								</tr>
							</thead>
							<tbody>${rows}</tbody>
						</table>
					`);
				},
				error() {
					page.btn_primary
						.prop("disabled", false)
						.text(__("Generate Summaries for All Active Employees"));
					$results.html(
						'<div class="alert alert-danger">' + __("Server error — check Error Log.") + "</div>"
					);
				},
			});
		},
		"fa fa-play"
	);
};
