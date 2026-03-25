
frappe.pages['manual_punch'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Manual Punch Entry',
        single_column: true
    });

    let today = frappe.datetime.get_today();
    let now = new Date();
    let hh = String(now.getHours()).padStart(2, '0');
    let mm = String(now.getMinutes()).padStart(2, '0');

    let html = `
    <div style="max-width:550px; margin:20px auto; background:white; padding:30px; border-radius:8px; border:1px solid #d1d8dd;">
        <div style="margin-bottom:15px">
            <label style="font-weight:bold; display:block; margin-bottom:5px; font-size:12px; color:#8D99A6;">EMPLOYEE</label>
            <select id="emp_select" class="form-control" style="background-color:#f4f5f6;">
                <option value="">-- Select Employee --</option>
            </select>
        </div>
        <div style="display:flex; gap:15px; margin-bottom:15px;">
            <div style="flex:1;">
                <label style="font-weight:bold; display:block; margin-bottom:5px; font-size:12px; color:#8D99A6;">DATE</label>
                <input type="date" id="punch_date" class="form-control" value="${today}" style="background-color:#f4f5f6;"/>
            </div>
            <div style="flex:1;">
                <label style="font-weight:bold; display:block; margin-bottom:5px; font-size:12px; color:#8D99A6;">TIME</label>
                <input type="time" id="punch_time" class="form-control" value="${hh}:${mm}" style="background-color:#f4f5f6;"/>
            </div>
        </div>
        <div style="margin-bottom:25px">
            <label style="font-weight:bold; display:block; margin-bottom:5px; font-size:12px; color:#8D99A6;">PUNCH TYPE</label>
            <div style="display:flex; gap:10px">
                <button id="btn_in" class="btn btn-default" style="flex:1; background-color:#2490ef; color:white; border:none;">● IN</button>
                <button id="btn_out" class="btn btn-default" style="flex:1; background-color:white; color:#36414C; border:1px solid #d1d8dd;">● OUT</button>
            </div>
        </div>
        <button id="btn_submit" class="btn btn-primary" style="width:100%; padding:10px; font-weight:bold;">
            Submit Manual Punch
        </button>
        <div id="punch_result" style="margin-top:15px; text-align:center;"></div>
        
        <div style="margin-top:30px; padding-top:20px; border-top:1px solid #d1d8dd;">
            <h6 style="margin-bottom:15px; color:#36414C; font-weight:bold;">RECENT MANUAL PUNCHES</h6>
            <table class="table table-bordered" style="font-size:12px; background:white;">
                <thead style="background-color:#f4f5f6;">
                    <tr>
                        <th>Employee</th>
                        <th>Time</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody id="recent_table">
                    <tr><td colspan="3" style="text-align:center; color:#8D99A6;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>`;

    // Inject directly into Frappe's main page container
    page.main.html(html);

    // Setup Interaction State
    let current_type = "IN";

    // Button Click Listeners
    page.main.find('#btn_in').on('click', function() {
        current_type = "IN";
        $(this).css({"background-color":"#2490ef", "color":"white", "border":"none"});
        page.main.find('#btn_out').css({"background-color":"white", "color":"#36414C", "border":"1px solid #d1d8dd"});
    });

    page.main.find('#btn_out').on('click', function() {
        current_type = "OUT";
        $(this).css({"background-color":"#2490ef", "color":"white", "border":"none"});
        page.main.find('#btn_in').css({"background-color":"white", "color":"#36414C", "border":"1px solid #d1d8dd"});
    });

    page.main.find('#btn_submit').on('click', function() {
        let employee = page.main.find("#emp_select").val();
        let date = page.main.find("#punch_date").val();
        let time = page.main.find("#punch_time").val() + ":00";
        
        if (!employee || !date || !page.main.find("#punch_time").val()) {
            frappe.msgprint({title: 'Error', message: 'Please fill all fields', indicator: 'red'});
            return;
        }

        $(this).prop("disabled", true).text("Submitting...");
        let btn = $(this);

        frappe.call({
            method: "biotime_erpgulf.attendance.add_manual_punch",
            args: { employee: employee, date: date, punch_time: time, log_type: current_type },
            callback: function(r) {
                btn.prop("disabled", false).text("Submit Manual Punch");
                if (r.message) {
                    page.main.find("#punch_result").html(
                        `<div style="padding:10px; background:#e2f2ea; color:#1b6343; border-radius:4px; font-weight:bold;">✅ ${r.message.message}</div>`
                    );
                    loadRecent();
                }
            },
            error: function() {
                btn.prop("disabled", false).text("Submit Manual Punch");
                page.main.find("#punch_result").html(
                    `<div style="padding:10px; background:#fbe6e8; color:#a1263c; border-radius:4px; font-weight:bold;">❌ Failed to add punch</div>`
                );
            }
        });
    });

    function loadRecent() {
        frappe.db.get_list("Employee Checkin", {
            filters: { device_id: "Manual" },
            fields: ["employee", "time", "log_type"],
            order_by: "time desc",
            limit: 8
        }).then(records => {
            let tbody = page.main.find("#recent_table");
            tbody.empty();
            if (!records.length) {
                tbody.html("<tr><td colspan=3 style='text-align:center; color:#8D99A6;'>No manual punches yet</td></tr>");
                return;
            }
            records.forEach(r => {
                let badge = r.log_type === "IN"
                    ? `<span class="badge" style="background-color:#e2f2ea; color:#1b6343;">IN</span>`
                    : `<span class="badge" style="background-color:#fbe6e8; color:#a1263c;">OUT</span>`;
                tbody.append(`<tr>
                    <td>${r.employee}</td>
                    <td>${r.time}</td>
                    <td>${badge}</td>
                </tr>`);
            });
        });
    }

    // Load Employee List
    frappe.call({
        method: "biotime_erpgulf.page.manual_punch.manual_punch.get_employees",
        callback: function(r) {
            if (r.message) {
                let sel = page.main.find("#emp_select");
                r.message.forEach(e => {
                    sel.append(`<option value="${e.name}">${e.employee_name} (${e.name})</option>`);
                });
            }
        }
    });

    loadRecent();
}
