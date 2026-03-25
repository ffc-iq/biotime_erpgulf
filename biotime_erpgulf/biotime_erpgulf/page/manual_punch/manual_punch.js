frappe.pages['manual_punch'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Manual Punch Entry',
		single_column: true
	});
}