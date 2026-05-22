let crews = [];
let currentTab = 'schedule';
let currentLeadFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    loadCrews().then(() => loadSchedule());
});

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    document.querySelector(`.nav-btn[data-tab="${tab}"]`).classList.add('active');

    if (tab === 'dashboard') loadDashboard();
    if (tab === 'schedule') loadSchedule();
    if (tab === 'jobs') loadAllJobs();
    if (tab === 'crews') loadCrewsList();
    if (tab === 'intake') loadLeads();
    if (tab === 'marketing') loadMarketing();
}

// ─── DASHBOARD ────────────────────────────────────────────────────────────────

const _charts = {};

async function loadDashboard() {
    const [s, roiData] = await Promise.all([
        apiFetch('/api/dashboard'),
        apiFetch('/api/marketing/roi'),
    ]);
    const cards = document.getElementById('dashboard-cards');
    if (!cards) return;

    const convHtml = s.conversion_rate != null
        ? `<div class="dash-stat">${s.conversion_rate}%</div><div class="dash-label">Win Rate</div>`
        : `<div class="dash-stat dash-na">—</div><div class="dash-label">Win Rate</div>`;

    cards.innerHTML = `
        <div class="dash-card dash-accent" onclick="switchTab('schedule')">
            <div class="dash-stat">${s.jobs_today}</div>
            <div class="dash-label">Jobs Today</div>
        </div>
        <div class="dash-card" onclick="switchTab('schedule')">
            <div class="dash-stat">${s.jobs_week}</div>
            <div class="dash-label">Jobs Next 7 Days</div>
        </div>
        <div class="dash-card dash-pipeline" onclick="switchTab('intake')">
            <div class="dash-pipeline-row">
                <span class="dp-box dp-intake" title="Intake">${s.leads_intake}<small>Intake</small></span>
                <span class="dp-arrow">→</span>
                <span class="dp-box dp-quoted" title="Quoted">${s.leads_quoted}<small>Quoted</small></span>
                <span class="dp-arrow">→</span>
                <span class="dp-box dp-won" title="Won">${s.leads_won}<small>Won</small></span>
                <span class="dp-sep">|</span>
                <span class="dp-box dp-lost" title="Lost">${s.leads_lost}<small>Lost</small></span>
            </div>
            <div class="dash-label">Lead Pipeline (click to open Intake)</div>
        </div>
        <div class="dash-card dash-conv">
            ${convHtml}
        </div>
    `;

    renderDashboardCharts(roiData);
}

function renderDashboardCharts(roiData) {
    const section = document.getElementById('dashboard-charts-section');
    if (!section) return;

    const active = roiData.filter(r => r.total_leads > 0 || r.source_id !== null);
    if (active.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';

    const labels = active.map(r => r.source_name);
    const colors = active.map(r => r.color || '#9CA3AF');

    function destroyAndCreate(key, canvasId, config) {
        if (_charts[key]) { try { _charts[key].destroy(); } catch(e){} }
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        _charts[key] = new Chart(ctx, config);
    }

    const chartDefaults = {
        plugins: { legend: { display: false } },
        responsive: true,
        maintainAspectRatio: false,
    };

    destroyAndCreate('revenue', 'chart-revenue', {
        type: 'bar',
        data: {
            labels,
            datasets: [{ data: active.map(r => r.total_revenue), backgroundColor: colors, borderRadius: 4 }],
        },
        options: {
            ...chartDefaults,
            scales: {
                y: { ticks: { callback: v => '$' + v.toLocaleString() }, grid: { color: '#f3f4f6' } },
                x: { grid: { display: false } },
            },
            plugins: { ...chartDefaults.plugins, tooltip: { callbacks: { label: ctx => ' $' + ctx.parsed.y.toLocaleString() } } },
        },
    });

    destroyAndCreate('leads', 'chart-leads', {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{ data: active.map(r => r.total_leads), backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }],
        },
        options: {
            ...chartDefaults,
            plugins: { legend: { display: true, position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 12 } } },
            cutout: '60%',
        },
    });

    const wrateData = active.map(r => r.win_rate ?? 0);
    const wrateColors = wrateData.map(v => v >= 70 ? '#10B981' : v >= 40 ? '#F59E0B' : '#EF4444');
    destroyAndCreate('winrate', 'chart-winrate', {
        type: 'bar',
        data: {
            labels,
            datasets: [{ data: wrateData, backgroundColor: wrateColors, borderRadius: 4 }],
        },
        options: {
            ...chartDefaults,
            indexAxis: 'y',
            scales: {
                x: { max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } },
                y: { grid: { display: false } },
            },
            plugins: { ...chartDefaults.plugins, tooltip: { callbacks: { label: ctx => ' ' + ctx.parsed.x + '%' } } },
        },
    });
}

async function apiFetch(url, opts = {}) {
    if (opts.body && typeof opts.body === 'object') {
        opts.body = JSON.stringify(opts.body);
        opts.headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    }
    const res = await fetch(url, opts);
    return res.json();
}

function showToast(msg, type = 'info') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + type + ' show';
    setTimeout(() => t.classList.remove('show'), 4000);
}

// DATE NAV
function changeDate(dir) {
    const input = document.getElementById('schedule-date');
    const d = new Date(input.value);
    d.setDate(d.getDate() + dir);
    input.value = d.toISOString().split('T')[0];
    loadSchedule();
}

function goToToday() {
    document.getElementById('schedule-date').value = new Date().toISOString().split('T')[0];
    loadSchedule();
}

// CREWS
async function loadCrews() {
    crews = await apiFetch('/api/crews');
}

function loadCrewsList() {
    const container = document.getElementById('crews-list');
    if (!crews.length) {
        container.innerHTML = '<p class="no-jobs-msg">No crews configured. Add a crew to get started.</p>';
        return;
    }
    container.innerHTML = '<div class="crews-grid">' + crews.map(c => `
        <div class="crew-card" style="border-left-color:${c.color}">
            <div class="crew-info">
                <h3>${esc(c.name)}</h3>
                <p>${esc(c.email)}</p>
            </div>
            <div class="crew-actions">
                <button class="btn btn-icon btn-sm" onclick="editCrew(${c.id})" title="Edit">&#9998;</button>
                <button class="btn btn-icon btn-sm" onclick="deleteCrew(${c.id})" title="Delete">&#10005;</button>
            </div>
        </div>
    `).join('') + '</div>';
}

function openCrewModal(crew = null) {
    document.getElementById('crew-modal-title').textContent = crew ? 'Edit Crew' : 'Add New Crew';
    document.getElementById('crew-id').value = crew ? crew.id : '';
    document.getElementById('crew-name').value = crew ? crew.name : '';
    document.getElementById('crew-email').value = crew ? crew.email : '';
    document.getElementById('crew-color').value = crew ? crew.color : '#3B82F6';
    document.getElementById('crew-modal').classList.add('open');
}

function closeCrewModal() {
    document.getElementById('crew-modal').classList.remove('open');
}

function editCrew(id) {
    const crew = crews.find(c => c.id === id);
    if (crew) openCrewModal(crew);
}

async function saveCrew(e) {
    e.preventDefault();
    const id = document.getElementById('crew-id').value;
    const data = {
        name: document.getElementById('crew-name').value,
        email: document.getElementById('crew-email').value,
        color: document.getElementById('crew-color').value
    };
    if (id) {
        await apiFetch('/api/crews/' + id, { method: 'PUT', body: data });
        showToast('Crew updated', 'success');
    } else {
        const res = await apiFetch('/api/crews', { method: 'POST', body: data });
        if (!res.success) { showToast(res.error, 'error'); return; }
        showToast('Crew added', 'success');
    }
    closeCrewModal();
    await loadCrews();
    loadCrewsList();
}

async function deleteCrew(id) {
    if (!confirm('Delete this crew?')) return;
    const res = await apiFetch('/api/crews/' + id, { method: 'DELETE' });
    if (!res.success) { showToast(res.error, 'error'); return; }
    showToast('Crew deleted', 'success');
    await loadCrews();
    loadCrewsList();
}

// JOBS
function populateCrewDropdown() {
    const sel = document.getElementById('job-crew');
    sel.innerHTML = '<option value="">-- Select Crew --</option>' +
        crews.map(c => `<option value="${c.id}">${esc(c.name)} (${esc(c.email)})</option>`).join('');
}

async function openJobModal(job = null, prefill = null) {
    populateCrewDropdown();
    const isEdit = !!job;
    const fromLead = !!prefill;
    document.getElementById('job-modal-title').textContent = isEdit ? 'Edit Job Assignment' : (fromLead ? 'Create Job from Intake' : 'Add New Job Assignment');
    document.getElementById('job-submit-btn').textContent = isEdit ? 'Update Job' : 'Add Job';
    document.getElementById('job-id').value = job ? job.id : '';
    document.getElementById('job-from-lead-id').value = prefill ? (prefill._lead_id || '') : '';

    document.getElementById('job-name').value = job ? job.job_name : (prefill ? (prefill.job_name || '') : '');

    // Feature 1: Auto-suggest project number for new jobs
    if (!job) {
        const projField = document.getElementById('job-project');
        projField.value = 'Loading…';
        apiFetch('/api/jobs/next-project-number').then(r => {
            if (projField.value === 'Loading…') projField.value = r.project_number || '';
        });
    } else {
        document.getElementById('job-project').value = job.project_number;
    }

    document.getElementById('job-address').value = job ? job.job_address : (prefill ? (prefill.job_address || '') : '');
    document.getElementById('job-crew').value = job ? job.crew_id : '';
    document.getElementById('job-scope').value = job ? job.scope_of_work : (prefill ? (prefill.scope_of_work || '') : '');
    document.getElementById('job-client-name').value = job ? (job.client_contact_name || '') : (prefill ? (prefill.client_contact_name || '') : '');
    document.getElementById('job-client-phone').value = job ? (job.client_phone || '') : (prefill ? (prefill.client_phone || '') : '');
    document.getElementById('job-date').value = job ? job.scheduled_date : document.getElementById('schedule-date').value;
    document.getElementById('job-time').value = job ? job.scheduled_start_time : '07:00';
    document.getElementById('job-duration').value = job ? job.estimated_duration : 4;
    document.getElementById('job-notes').value = job ? (job.notes || '') : (prefill ? (prefill.notes || '') : '');
    const toolsSelect = document.getElementById('job-tools');
    Array.from(toolsSelect.options).forEach(opt => {
        opt.selected = job ? (job.tools_required || '').split(',').includes(opt.value) : false;
    });
    document.getElementById('job-invite-notes').value = job ? (job.invite_notes || '') : (prefill ? (prefill.invite_notes || '') : '');
    document.getElementById('job-send-invite').checked = true;
    document.getElementById('job-modal').classList.add('open');
}

async function openJobModalFromLead(leadId) {
    const lead = await apiFetch('/api/leads/' + leadId);
    if (lead.error) { showToast('Lead not found', 'error'); return; }

    // Build a scope value matching the dropdown options
    const scopeMap = {
        'Boundary': 'Boundary Survey',
        'Topographic': 'Topographic Survey',
        'Construction Staking': 'Construction Staking',
        'Title (1A/1B/ALTA)': 'Boundary Survey',
        'Lot Split/Subdividing': 'Boundary Survey',
        'Combine Lots': 'Boundary Survey'
    };
    const surveyTypes = (lead.survey_types || '').split(',').map(s => s.trim()).filter(Boolean);
    let scope = lead.scope_of_work || '';
    if (!scope && surveyTypes.length) {
        scope = scopeMap[surveyTypes[0]] || surveyTypes[0];
    }

    // Build crew brief for Notes field
    const lines = [];
    if (lead.key_notes) lines.push('SUMMARY: ' + lead.key_notes);
    if (lead.property_owner && lead.property_owner !== lead.client_name) lines.push('Property Owner: ' + lead.property_owner);
    if (surveyTypes.length) lines.push('Survey Type(s): ' + surveyTypes.join(', '));
    if (lead.property_type) lines.push('Property Type: ' + lead.property_type);
    if (lead.property_size) lines.push('Property Size: ' + lead.property_size);
    if (lead.property_condition) lines.push('Property Condition: ' + lead.property_condition);
    if (lead.improvements) lines.push('Improvements: ' + lead.improvements + (lead.improvements_other ? ', ' + lead.improvements_other : ''));
    if (lead.terrain) lines.push('Terrain: ' + lead.terrain + (lead.terrain_details ? ' — ' + lead.terrain_details : ''));
    if (lead.site_risks || lead.site_risks_other) lines.push('⚠ Site Risks: ' + [lead.site_risks, lead.site_risks_other].filter(Boolean).join(', '));
    if (lead.access_type) lines.push('Access: ' + lead.access_type);
    if (lead.existing_documents) lines.push('Existing Docs: ' + lead.existing_documents);
    if (lead.existing_markers) lines.push('Existing Markers: ' + lead.existing_markers);
    if (lead.staking) lines.push('Staking: ' + lead.staking);
    if (lead.disputes && lead.disputes !== 'None') lines.push('Disputes/Encroachments: ' + lead.disputes + (lead.disputes_details ? ' — ' + lead.disputes_details : ''));
    if (lead.deliverables) lines.push('Deliverables: ' + lead.deliverables + (lead.deliverables_other ? ', ' + lead.deliverables_other : ''));
    if (lead.coordination && lead.coordination !== 'None') lines.push('Coordination: ' + lead.coordination + (lead.coordination_details ? ' — ' + lead.coordination_details : ''));
    if (lead.description) lines.push('\nNotes: ' + lead.description);

    // Build invite notes (field-crew-facing info)
    const inviteLines = [];
    if (lead.access_type) inviteLines.push('Access: ' + lead.access_type);
    if (lead.site_risks || lead.site_risks_other) inviteLines.push('Site Risks: ' + [lead.site_risks, lead.site_risks_other].filter(Boolean).join(', '));
    if (lead.terrain) inviteLines.push('Terrain: ' + lead.terrain);
    if (lead.staking) inviteLines.push('Staking: ' + lead.staking);
    if (lead.deliverables) inviteLines.push('Deliverables: ' + lead.deliverables);

    const ownerName = lead.property_owner || lead.client_name;
    const prefill = {
        _lead_id: lead.id,
        job_name: ownerName + (scope ? ' — ' + scope : ''),
        job_address: lead.property_address || '',
        scope_of_work: scope,
        client_contact_name: lead.client_name || '',
        client_phone: lead.client_phone || '',
        notes: lines.join('\n'),
        invite_notes: inviteLines.join('\n')
    };

    openJobModal(null, prefill);
}

function closeJobModal() {
    document.getElementById('job-modal').classList.remove('open');
}

async function saveJob(e) {
    e.preventDefault();
    const id = document.getElementById('job-id').value;
    const fromLeadId = document.getElementById('job-from-lead-id').value;
    const data = {
        job_name: document.getElementById('job-name').value,
        project_number: document.getElementById('job-project').value,
        job_address: document.getElementById('job-address').value,
        crew_id: parseInt(document.getElementById('job-crew').value),
        scope_of_work: document.getElementById('job-scope').value,
        client_contact_name: document.getElementById('job-client-name').value,
        client_phone: document.getElementById('job-client-phone').value,
        scheduled_date: document.getElementById('job-date').value,
        scheduled_start_time: document.getElementById('job-time').value,
        estimated_duration: parseFloat(document.getElementById('job-duration').value),
        notes: document.getElementById('job-notes').value,
        tools_required: Array.from(document.getElementById('job-tools').selectedOptions).map(o => o.value).join(','),
        invite_notes: document.getElementById('job-invite-notes').value,
        send_invite: document.getElementById('job-send-invite').checked
    };

    let res;
    if (id) {
        res = await apiFetch('/api/jobs/' + id, { method: 'PUT', body: data });
    } else {
        res = await apiFetch('/api/jobs', { method: 'POST', body: data });
    }

    if (res.success) {
        let msg = id ? 'Job updated' : 'Job created';
        if (res.email_sent) msg += ' and invite sent';
        else if (res.email_message && res.email_message !== 'Email not attempted') msg += ' (email: ' + res.email_message + ')';

        // If created from an intake lead, mark the lead as won and link the job
        if (!id && fromLeadId && res.job_id) {
            await apiFetch('/api/leads/' + fromLeadId + '/won', {
                method: 'POST',
                body: { job_id: res.job_id }
            });
            msg += ' — Intake marked as Won';
            if (currentTab === 'intake') loadLeads();
        }

        showToast(msg, 'success');
    } else {
        showToast(res.error || 'Error saving job', 'error');
        return;
    }

    closeJobModal();
    if (currentTab === 'schedule') loadSchedule();
    if (currentTab === 'jobs') loadAllJobs();
}

async function editJob(id) {
    const job = await apiFetch('/api/jobs/' + id);
    if (job.error) { showToast('Job not found', 'error'); return; }
    openJobModal(job);
}

async function deleteJob(id) {
    if (!confirm('Delete this job? A cancellation will be sent to the crew.')) return;
    const res = await apiFetch('/api/jobs/' + id, { method: 'DELETE' });
    if (res.success) {
        showToast('Job deleted', 'success');
        if (currentTab === 'schedule') loadSchedule();
        if (currentTab === 'jobs') loadAllJobs();
    } else {
        showToast(res.error || 'Error', 'error');
    }
}

async function cancelJob(id) {
    if (!confirm('Cancel this job? A cancellation notice will be sent to the crew.')) return;
    const res = await apiFetch('/api/jobs/' + id + '/cancel', { method: 'POST' });
    if (res.success) {
        showToast('Job cancelled and crew notified', 'success');
        if (currentTab === 'schedule') loadSchedule();
        if (currentTab === 'jobs') loadAllJobs();
    } else {
        showToast(res.error || 'Error cancelling job', 'error');
    }
}

async function sendManualUpdate(id) {
    const res = await apiFetch('/api/send-update/' + id, { method: 'POST' });
    showToast(res.message || (res.success ? 'Update sent' : 'Failed to send'), res.success ? 'success' : 'error');
}

// SCHEDULE VIEW
async function loadSchedule() {
    const date = document.getElementById('schedule-date').value;
    const jobs = await apiFetch('/api/jobs?date=' + date);

    const container = document.getElementById('schedule-view');
    if (!crews.length) {
        container.innerHTML = '<div class="no-jobs-msg">No crews configured. Go to Crews tab to add crews.</div>';
        return;
    }

    const startHour = 5;
    const endHour = 20;
    const hours = [];
    for (let h = startHour; h <= endHour; h++) {
        const label = h === 0 ? '12 AM' : h < 12 ? h + ' AM' : h === 12 ? '12 PM' : (h - 12) + ' PM';
        hours.push({ h, label });
    }

    const selDate = new Date(date + 'T00:00:00');
    const dayOfWeek = selDate.getDay();
    const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    const monday = new Date(selDate);
    monday.setDate(monday.getDate() + mondayOffset);
    const weekStart = monday.toISOString().split('T')[0];

    let html = '<div class="schedule-header"><div class="time-col">Time</div>';
    html += `<div class="crews-header" style="grid-template-columns:repeat(${crews.length},1fr)">`;
    crews.forEach(c => {
        html += `<div class="crew-col-header" style="background:${c.color}">
            ${esc(c.name)}
            <a class="crew-weekly-link" href="/api/crews/${c.id}/weekly.ics?week=${weekStart}" title="Download ${esc(c.name)}'s weekly schedule">&#128197; Weekly</a>
        </div>`;
    });
    html += '</div></div>';

    html += '<div class="schedule-body"><div class="time-labels">';
    hours.forEach(h => {
        html += `<div class="time-label">${h.label}</div>`;
    });
    html += '</div>';

    html += `<div class="crew-columns" style="grid-template-columns:repeat(${crews.length},1fr)">`;
    crews.forEach(c => {
        html += '<div class="crew-column">';
        hours.forEach(() => { html += '<div class="hour-line"></div>'; });

        const crewJobs = jobs.filter(j => j.crew_id === c.id);
        crewJobs.forEach(j => {
            const [hh, mm] = j.scheduled_start_time.split(':').map(Number);
            const topMin = (hh - startHour) * 60 + mm;
            const top = topMin;
            const height = Math.max(j.estimated_duration * 60, 30);

            html += `<div class="job-block" style="top:${top}px;height:${height}px;background:${c.color}"
                          onclick="editJob(${j.id})" title="${esc(j.job_name)}&#10;${esc(j.project_number)}&#10;${esc(j.scope_of_work)}">
                <div class="job-block-title">${esc(j.project_number)}</div>
                <div class="job-block-detail">${esc(j.scope_of_work)}</div>
                <div class="job-block-detail">${esc(j.job_name)}</div>
                <a class="job-download-link" href="/api/jobs/${j.id}/download.ics" onclick="event.stopPropagation()" title="Download calendar invite">&#128197; Download Invite</a>
            </div>`;
        });

        html += '</div>';
    });
    html += '</div></div>';

    if (!jobs.length) {
        html += '<div class="no-jobs-msg">No jobs scheduled for this date. Click "+ Add Job" to create one.</div>';
    }

    container.innerHTML = html;
}

// ALL JOBS TABLE
async function loadAllJobs() {
    const jobs = await apiFetch('/api/jobs');
    const tbody = document.getElementById('jobs-tbody');
    if (!jobs.length) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:40px;color:#6B7280">No jobs found.</td></tr>';
        return;
    }
    tbody.innerHTML = jobs.map(j => `
        <tr>
            <td>${j.scheduled_date}</td>
            <td>${formatTime(j.scheduled_start_time)}</td>
            <td><strong>${esc(j.project_number)}</strong></td>
            <td>${esc(j.job_name)}</td>
            <td><span class="crew-badge" style="background:${j.crew_color}"><span class="dot"></span>${esc(j.crew_name)}</span></td>
            <td>${esc(j.scope_of_work)}</td>
            <td>${esc(j.job_address)}</td>
            <td>${j.status === 'cancelled' ? '<span class="status-cancelled">Cancelled</span>' : '<span class="status-active">Active</span>'}</td>
            <td class="actions">
                <button class="btn btn-icon btn-sm" onclick="editJob(${j.id})" title="Edit">&#9998;</button>
                <a class="btn btn-icon btn-sm" href="/api/jobs/${j.id}/download.ics" title="Download Invite">&#128197;</a>
                <button class="btn btn-icon btn-sm" onclick="sendManualUpdate(${j.id})" title="Send Update">&#9993;</button>
                ${j.status !== 'cancelled' ? `<button class="btn btn-icon btn-sm" onclick="cancelJob(${j.id})" title="Cancel Job">&#10008;</button>` : ''}
                <button class="btn btn-icon btn-sm" onclick="deleteJob(${j.id})" title="Delete">&#10005;</button>
            </td>
        </tr>
    `).join('');
}

// SEND TOMORROW
async function sendTomorrow() {
    if (!confirm("Send tomorrow's schedule to all assigned crews?")) return;
    const res = await apiFetch('/api/send-tomorrow', { method: 'POST' });
    if (res.message) {
        showToast(res.message, res.success ? 'success' : 'info');
    } else if (res.results) {
        const ok = res.results.filter(r => r.success).length;
        const fail = res.results.filter(r => !r.success).length;
        showToast(`Sent: ${ok} | Failed: ${fail}`, ok > 0 ? 'success' : 'error');
    }
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');
}

function openTestInviteModal() {
    document.getElementById('test-invite-email').value = '';
    document.getElementById('test-invite-modal').classList.add('open');
}

async function sendTestInvite() {
    const email = document.getElementById('test-invite-email').value.trim();
    if (!email || !email.includes('@')) {
        showToast('Enter a valid email address.', 'error');
        return;
    }
    showToast('Sending test invite…', 'info');
    const res = await apiFetch('/api/test-invite', { method: 'POST', body: { to_email: email } });
    if (res) {
        showToast(res.message, res.success ? 'success' : 'error');
        if (res.success) closeModal('test-invite-modal');
    }
}

// ─── MARKETING / LEAD SOURCES ─────────────────────────────────────────────────

let leadSources = [];

async function loadMarketing() {
    await Promise.all([loadLeadSources(), loadMarketingROI()]);
}

async function loadLeadSources() {
    leadSources = await apiFetch('/api/lead-sources');
    const wrap = document.getElementById('lead-sources-list');
    if (!wrap) return;

    if (!leadSources.length) {
        wrap.innerHTML = '<div class="no-jobs-msg">No lead sources defined yet. Click <strong>+ Add Source</strong> to get started.</div>';
        return;
    }

    wrap.innerHTML = `
        <table class="lead-sources-table">
            <thead>
                <tr>
                    <th>Source Name</th>
                    <th>Monthly Budget</th>
                    <th>Color</th>
                    <th style="text-align:right">Actions</th>
                </tr>
            </thead>
            <tbody>
                ${leadSources.map(s => `
                <tr>
                    <td><div class="source-name-cell"><span class="color-swatch" style="background:${s.color}"></span>${s.name}</div></td>
                    <td>${s.monthly_budget > 0 ? '$' + parseFloat(s.monthly_budget).toLocaleString('en-US', {minimumFractionDigits:2}) : '—'}</td>
                    <td><span class="color-swatch" style="background:${s.color}"></span>${s.color}</td>
                    <td style="text-align:right">
                        <button class="btn btn-sm btn-outline" onclick="openLeadSourceModal(${s.id})" style="margin-right:6px">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteLeadSource(${s.id}, '${s.name.replace(/'/g,"\\'")}')">Delete</button>
                    </td>
                </tr>`).join('')}
            </tbody>
        </table>`;
}

async function loadMarketingROI() {
    const data = await apiFetch('/api/marketing/roi');
    const wrap = document.getElementById('roi-table-wrap');
    if (!wrap) return;

    const active = data.filter(r => r.total_leads > 0);
    if (!active.length) {
        wrap.innerHTML = '<div class="no-jobs-msg">No lead data yet. Tag leads with a source in the Intake form to see ROI stats.</div>';
        return;
    }

    const fmt$ = v => v != null && v > 0 ? '$' + parseFloat(v).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2}) : '<span class="roi-na">—</span>';
    const fmtWR = r => {
        if (r.win_rate == null) return '<span class="roi-na">—</span>';
        const cls = r.win_rate >= 70 ? 'background:#dcfce7;color:#166534' : r.win_rate >= 40 ? 'background:#fef9c3;color:#854d0e' : 'background:#fee2e2;color:#991b1b';
        return `<span class="roi-win-rate" style="${cls}">${r.win_rate}%</span>`;
    };

    const totals = active.reduce((acc, r) => ({
        leads: acc.leads + r.total_leads,
        quoted: acc.quoted + r.quoted_count,
        won: acc.won + r.won_count,
        lost: acc.lost + r.lost_count,
        revenue: acc.revenue + r.total_revenue,
    }), {leads:0,quoted:0,won:0,lost:0,revenue:0});
    const totalWR = totals.won + totals.lost > 0 ? Math.round(totals.won/(totals.won+totals.lost)*100) : null;

    wrap.innerHTML = `
        <div style="overflow-x:auto">
        <table class="roi-table">
            <thead>
                <tr>
                    <th>Source</th>
                    <th>Leads</th>
                    <th>Quoted</th>
                    <th>Won</th>
                    <th>Lost</th>
                    <th>Win Rate</th>
                    <th>Revenue Won</th>
                    <th>Monthly Budget</th>
                    <th>Cost / Lead</th>
                    <th>Cost / Acq.</th>
                </tr>
            </thead>
            <tbody>
                ${active.map(r => `
                <tr>
                    <td><div class="source-name-cell"><span class="color-swatch" style="background:${r.color}"></span>${r.source_name}</div></td>
                    <td>${r.total_leads}</td>
                    <td>${r.quoted_count}</td>
                    <td>${r.won_count}</td>
                    <td>${r.lost_count}</td>
                    <td>${fmtWR(r)}</td>
                    <td>${fmt$(r.total_revenue)}</td>
                    <td>${r.monthly_budget > 0 ? '$'+parseFloat(r.monthly_budget).toLocaleString('en-US',{minimumFractionDigits:2}) : '—'}</td>
                    <td>${fmt$(r.cost_per_lead)}</td>
                    <td>${fmt$(r.cost_per_acq)}</td>
                </tr>`).join('')}
            </tbody>
            <tfoot>
                <tr class="roi-total-row">
                    <td>Total</td>
                    <td>${totals.leads}</td>
                    <td>${totals.quoted}</td>
                    <td>${totals.won}</td>
                    <td>${totals.lost}</td>
                    <td>${totalWR != null ? `<span class="roi-win-rate" style="${totalWR>=70?'background:#dcfce7;color:#166534':totalWR>=40?'background:#fef9c3;color:#854d0e':'background:#fee2e2;color:#991b1b'}">${totalWR}%</span>` : '<span class="roi-na">—</span>'}</td>
                    <td>${fmt$(totals.revenue)}</td>
                    <td>—</td><td>—</td><td>—</td>
                </tr>
            </tfoot>
        </table>
        </div>`;
}

function openLeadSourceModal(id) {
    document.getElementById('ls-modal-title').textContent = id ? 'Edit Lead Source' : 'Add Lead Source';
    document.getElementById('ls-id').value = id || '';
    document.getElementById('ls-name').value = '';
    document.getElementById('ls-budget').value = '0';
    document.getElementById('ls-color').value = '#3B82F6';

    if (id) {
        const src = leadSources.find(s => s.id === id);
        if (src) {
            document.getElementById('ls-name').value = src.name;
            document.getElementById('ls-budget').value = src.monthly_budget || 0;
            document.getElementById('ls-color').value = src.color || '#3B82F6';
        }
    }
    document.getElementById('lead-source-modal').classList.add('open');
}

async function saveLeadSource() {
    const id = document.getElementById('ls-id').value;
    const name = document.getElementById('ls-name').value.trim();
    const budget = parseFloat(document.getElementById('ls-budget').value) || 0;
    const color = document.getElementById('ls-color').value;

    if (!name) { showToast('Source name is required.', 'error'); return; }

    const body = { name, monthly_budget: budget, color };
    let res;
    if (id) {
        res = await apiFetch(`/api/lead-sources/${id}`, { method: 'PUT', body });
    } else {
        res = await apiFetch('/api/lead-sources', { method: 'POST', body });
    }

    if (res && res.success) {
        showToast(id ? 'Lead source updated.' : 'Lead source added.', 'success');
        closeModal('lead-source-modal');
        loadMarketing();
    } else {
        showToast((res && res.error) || 'Error saving lead source.', 'error');
    }
}

async function deleteLeadSource(id, name) {
    if (!confirm(`Delete lead source "${name}"? Leads tagged with this source will become Unassigned.`)) return;
    const res = await apiFetch(`/api/lead-sources/${id}`, { method: 'DELETE' });
    if (res && res.success) {
        showToast('Lead source deleted.', 'success');
        loadMarketing();
    }
}

async function populateLeadSourceDropdown() {
    const sel = document.getElementById('lead-source-id');
    if (!sel) return;
    const sources = await apiFetch('/api/lead-sources');
    leadSources = sources;
    const current = sel.value;
    sel.innerHTML = '<option value="">-- How did they find us? --</option>' +
        sources.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    if (current) sel.value = current;
}

// ─── INTAKE / LEADS ───────────────────────────────────────────────────────────

function setLeadFilter(filter, btn) {
    currentLeadFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadLeads();
}

async function loadLeads() {
    const url = '/api/leads' + (currentLeadFilter !== 'all' ? '?status=' + currentLeadFilter : '');
    const leads = await apiFetch(url);
    const tbody = document.getElementById('intake-tbody');
    if (!leads.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:40px;color:#6B7280">No records found.</td></tr>';
        return;
    }
    tbody.innerHTML = leads.map(l => {
        const date = l.created_at ? l.created_at.split('T')[0] : '';
        const addr = [l.property_address, l.county].filter(Boolean).join(' &mdash; ');
        const quote = l.quote_amount != null ? '$' + parseFloat(l.quote_amount).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '<span style="color:#9CA3AF">None</span>';
        const statusBadge = leadStatusBadge(l.status);

        // Feature 3: aging badge for quoted leads
        let agingBadge = '';
        if (l.status === 'quoted' && l.quote_date) {
            const days = Math.floor((Date.now() - new Date(l.quote_date).getTime()) / 86400000);
            if (days >= 7) agingBadge = `<span class="age-badge age-red" title="${days} days since quote">${days}d old</span>`;
            else if (days >= 3) agingBadge = `<span class="age-badge age-yellow" title="${days} days since quote">${days}d old</span>`;
            else if (days >= 1) agingBadge = `<span class="age-badge age-grey" title="${days} days since quote">${days}d old</span>`;
        }

        // Feature 6: clickable job link
        const wonJobLink = l.status === 'won' && l.job_id
            ? `<button class="btn-job-link" onclick="jumpToJob(${l.job_id})" title="View job in All Jobs tab">&#128279; View Job</button>`
            : '';
        let actions = `<button class="btn btn-icon btn-sm" onclick="editLead(${l.id})" title="Edit">&#9998;</button>`;
        if (l.status !== 'won' && l.status !== 'lost') {
            actions += `<button class="btn btn-icon btn-sm" onclick="openQuoteModal(${l.id})" title="Record Quote">&#128181;</button>`;
        }
        if (l.status === 'quoted') {
            actions += `<button class="btn btn-icon btn-sm btn-won" onclick="markWon(${l.id})" title="Client accepted — create job">&#10003; Go Live</button>`;
            actions += `<button class="btn btn-icon btn-sm btn-lost" onclick="openLostModal(${l.id})" title="Mark Lost">&#10005; Lost</button>`;
        }
        if (l.status === 'intake') {
            actions += `<button class="btn btn-icon btn-sm btn-won" onclick="markWon(${l.id})" title="Client accepted — create job">&#10003; Go Live</button>`;
            actions += `<button class="btn btn-icon btn-sm btn-lost" onclick="openLostModal(${l.id})" title="Mark Lost">&#10005; Lost</button>`;
        }
        if (l.status === 'won' && !l.job_id) {
            actions += `<button class="btn btn-icon btn-sm btn-won" onclick="openJobModalFromLead(${l.id})" title="Create job from this intake">+ Create Job</button>`;
        }
        actions += `<button class="btn btn-icon btn-sm" onclick="deleteLead(${l.id})" title="Delete">&#128465;</button>`;
        return `<tr>
            <td>${date}</td>
            <td>
                <strong>${esc(l.client_name)}</strong>
                ${l.client_email ? `<br><small style="color:#6B7280">${esc(l.client_email)}</small>` : ''}
            </td>
            <td>${esc(l.client_phone || '')}</td>
            <td>${addr || '<span style="color:#9CA3AF">—</span>'}</td>
            <td>${esc(l.scope_of_work || '')}</td>
            <td>
                ${quote}
                ${l.quote_notes ? `<br><small style="color:#6B7280">${esc(l.quote_notes.substring(0, 40))}${l.quote_notes.length > 40 ? '...' : ''}</small>` : ''}
            </td>
            <td>${statusBadge}${agingBadge}${wonJobLink}</td>
            <td class="actions">${actions}</td>
        </tr>`;
    }).join('');
}

function leadStatusBadge(status) {
    const map = {
        intake: '<span class="status-intake">Intake</span>',
        quoted: '<span class="status-quoted">Quoted</span>',
        won: '<span class="status-won">Won</span>',
        lost: '<span class="status-lost">Lost</span>'
    };
    return map[status] || `<span>${status}</span>`;
}

function _setRadio(name, value) {
    document.querySelectorAll(`input[name="${name}"]`).forEach(r => { r.checked = r.value === value; });
}
function _getRadio(name) {
    const r = document.querySelector(`input[name="${name}"]:checked`);
    return r ? r.value : '';
}
function _setCheckboxes(cls, valueStr) {
    const vals = (valueStr || '').split(',').map(v => v.trim()).filter(Boolean);
    document.querySelectorAll(`input.${cls}`).forEach(cb => { cb.checked = vals.includes(cb.value); });
}
function _getCheckboxes(cls) {
    return Array.from(document.querySelectorAll(`input.${cls}:checked`)).map(cb => cb.value).join(', ');
}

function openLeadModal(lead = null) {
    const isEdit = !!lead;
    document.getElementById('lead-modal-title').textContent = isEdit ? 'Edit Survey Request' : 'Survey Request Form';
    document.getElementById('lead-submit-btn').textContent = isEdit ? 'Update' : 'Save Intake';
    document.getElementById('lead-id').value = lead ? lead.id : '';

    // Section 1
    populateLeadSourceDropdown().then(() => {
        const sel = document.getElementById('lead-source-id');
        if (sel) sel.value = lead ? (lead.lead_source_id || '') : '';
    });
    document.getElementById('lead-survey-type').value = lead ? (lead.scope_of_work || '') : '';
    document.getElementById('lead-property-size').value = lead ? (lead.property_size || '') : '';
    document.getElementById('lead-deadline').value = lead ? (lead.deadline || '') : '';
    document.getElementById('lead-key-notes').value = lead ? (lead.key_notes || '') : '';

    // Section 2
    document.getElementById('lead-client-name').value = lead ? lead.client_name : '';
    document.getElementById('lead-property-owner').value = lead ? (lead.property_owner || '') : '';
    document.getElementById('lead-client-phone').value = lead ? (lead.client_phone || '') : '';
    document.getElementById('lead-client-email').value = lead ? (lead.client_email || '') : '';

    // Section 3
    document.getElementById('lead-address').value = lead ? (lead.property_address || '') : '';
    document.getElementById('lead-county').value = lead ? (lead.county || '') : '';
    document.getElementById('lead-approx-size').value = lead ? (lead.property_size || '') : '';
    _setRadio('prop-type', lead ? (lead.property_type || '') : '');
    _setCheckboxes('survey-purpose', lead ? (lead.survey_purpose || '') : '');
    document.getElementById('lead-survey-purpose-other').value = lead ? (lead.survey_purpose_other || '') : '';

    // Section 4
    _setRadio('prop-condition', lead ? (lead.property_condition || '') : '');
    _setCheckboxes('improvements', lead ? (lead.improvements || '') : '');
    document.getElementById('lead-improvements-other').value = lead ? (lead.improvements_other || '') : '';
    _setCheckboxes('terrain', lead ? (lead.terrain || '') : '');
    document.getElementById('lead-terrain-details').value = lead ? (lead.terrain_details || '') : '';

    // Section 5
    _setCheckboxes('site-risks', lead ? (lead.site_risks || '') : '');
    document.getElementById('lead-risks-other').value = lead ? (lead.site_risks_other || '') : '';

    // Section 6
    _setRadio('access', lead ? (lead.access_type || '') : '');

    // Section 7
    _setCheckboxes('exist-docs', lead ? (lead.existing_documents || '') : '');
    _setCheckboxes('exist-markers', lead ? (lead.existing_markers || '') : '');

    // Section 8
    _setCheckboxes('survey-types', lead ? (lead.survey_types || '') : '');

    // Section 9
    _setRadio('staking', lead ? (lead.staking || '') : '');

    // Section 10
    _setRadio('disputes', lead ? (lead.disputes || '') : '');
    document.getElementById('lead-disputes-details').value = lead ? (lead.disputes_details || '') : '';

    // Section 11
    document.getElementById('lead-needed-by').value = lead ? (lead.timeline_needed_by || '') : '';
    _setRadio('timeline-type', lead ? (lead.timeline_type || '') : '');
    document.getElementById('lead-timeline-other').value = lead ? (lead.timeline_other || '') : '';

    // Section 12
    _setCheckboxes('deliverables', lead ? (lead.deliverables || '') : '');
    document.getElementById('lead-deliverables-other').value = lead ? (lead.deliverables_other || '') : '';

    // Section 13
    _setCheckboxes('coordination', lead ? (lead.coordination || '') : '');
    document.getElementById('lead-coordination-details').value = lead ? (lead.coordination_details || '') : '';

    // Section 14
    _setRadio('referral', lead ? (lead.referral_source || '') : '');
    document.getElementById('lead-referral-other').value = lead ? (lead.referral_source_other || '') : '';

    // Section 15
    document.getElementById('lead-description').value = lead ? (lead.description || '') : '';

    document.getElementById('lead-modal').classList.add('open');
    document.querySelector('#lead-modal .intake-form-body').scrollTop = 0;
}

function closeLeadModal() {
    document.getElementById('lead-modal').classList.remove('open');
}

async function editLead(id) {
    const lead = await apiFetch('/api/leads/' + id);
    if (lead.error) { showToast('Lead not found', 'error'); return; }
    openLeadModal(lead);
}

async function saveLead(e) {
    e.preventDefault();
    const id = document.getElementById('lead-id').value;
    const surveyType = document.getElementById('lead-survey-type').value;
    const leadSourceVal = document.getElementById('lead-source-id')?.value;
    const data = {
        // Section 1
        lead_source_id: leadSourceVal ? parseInt(leadSourceVal) : null,
        scope_of_work: surveyType,
        property_size: document.getElementById('lead-property-size').value,
        deadline: document.getElementById('lead-deadline').value,
        key_notes: document.getElementById('lead-key-notes').value,
        // Section 2
        client_name: document.getElementById('lead-client-name').value,
        caller_name: document.getElementById('lead-client-name').value,
        property_owner: document.getElementById('lead-property-owner').value,
        client_phone: document.getElementById('lead-client-phone').value,
        client_email: document.getElementById('lead-client-email').value,
        // Section 3
        property_address: document.getElementById('lead-address').value,
        county: document.getElementById('lead-county').value,
        property_type: _getRadio('prop-type'),
        survey_purpose: _getCheckboxes('survey-purpose'),
        survey_purpose_other: document.getElementById('lead-survey-purpose-other').value,
        // Section 4
        property_condition: _getRadio('prop-condition'),
        improvements: _getCheckboxes('improvements'),
        improvements_other: document.getElementById('lead-improvements-other').value,
        terrain: _getCheckboxes('terrain'),
        terrain_details: document.getElementById('lead-terrain-details').value,
        // Section 5
        site_risks: _getCheckboxes('site-risks'),
        site_risks_other: document.getElementById('lead-risks-other').value,
        // Section 6
        access_type: _getRadio('access'),
        // Section 7
        existing_documents: _getCheckboxes('exist-docs'),
        existing_markers: _getCheckboxes('exist-markers'),
        // Section 8
        survey_types: _getCheckboxes('survey-types'),
        // Section 9
        staking: _getRadio('staking'),
        // Section 10
        disputes: _getRadio('disputes'),
        disputes_details: document.getElementById('lead-disputes-details').value,
        // Section 11
        timeline_needed_by: document.getElementById('lead-needed-by').value,
        timeline_type: _getRadio('timeline-type'),
        timeline_other: document.getElementById('lead-timeline-other').value,
        // Section 12
        deliverables: _getCheckboxes('deliverables'),
        deliverables_other: document.getElementById('lead-deliverables-other').value,
        // Section 13
        coordination: _getCheckboxes('coordination'),
        coordination_details: document.getElementById('lead-coordination-details').value,
        // Section 14
        referral_source: _getRadio('referral'),
        referral_source_other: document.getElementById('lead-referral-other').value,
        // Section 15
        description: document.getElementById('lead-description').value
    };
    let res;
    if (id) {
        res = await apiFetch('/api/leads/' + id, { method: 'PUT', body: data });
    } else {
        res = await apiFetch('/api/leads', { method: 'POST', body: data });
    }
    if (res.success) {
        showToast(id ? 'Updated' : 'Intake saved', 'success');
        closeLeadModal();
        loadLeads();
    } else {
        showToast(res.error || 'Error saving', 'error');
    }
}

async function deleteLead(id) {
    if (!confirm('Delete this intake record?')) return;
    const res = await apiFetch('/api/leads/' + id, { method: 'DELETE' });
    if (res.success) { showToast('Deleted', 'success'); loadLeads(); }
    else showToast(res.error || 'Error', 'error');
}

function openQuoteModal(leadId) {
    document.getElementById('quote-lead-id').value = leadId;
    document.getElementById('quote-amount').value = '';
    document.getElementById('quote-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('quote-notes').value = '';
    document.getElementById('quote-modal').classList.add('open');
}

function closeQuoteModal() {
    document.getElementById('quote-modal').classList.remove('open');
}

async function saveQuote(e) {
    e.preventDefault();
    const leadId = document.getElementById('quote-lead-id').value;
    const data = {
        quote_amount: parseFloat(document.getElementById('quote-amount').value),
        quote_date: document.getElementById('quote-date').value,
        quote_notes: document.getElementById('quote-notes').value
    };
    const res = await apiFetch('/api/leads/' + leadId + '/quote', { method: 'POST', body: data });
    if (res.success) {
        showToast('Quote recorded', 'success');
        closeQuoteModal();
        loadLeads();
    } else {
        showToast(res.error || 'Error', 'error');
    }
}

async function markWon(leadId) {
    if (!confirm('Client accepted the quote? This will open the job form pre-filled with all intake details so you can schedule it.')) return;
    await openJobModalFromLead(leadId);
}

function openLostModal(leadId) {
    document.getElementById('lost-lead-id').value = leadId;
    document.getElementById('lost-reason').value = '';
    document.getElementById('lost-reason-select').value = '';
    document.getElementById('lost-modal').classList.add('open');
}

function closeLostModal() {
    document.getElementById('lost-modal').classList.remove('open');
}

function handleLostReasonSelect(sel) {
    if (sel.value && sel.value !== 'Other') {
        document.getElementById('lost-reason').value = sel.value;
    }
}

async function saveLost(e) {
    e.preventDefault();
    const leadId = document.getElementById('lost-lead-id').value;
    const data = { lost_reason: document.getElementById('lost-reason').value };
    const res = await apiFetch('/api/leads/' + leadId + '/lost', { method: 'POST', body: data });
    if (res.success) {
        showToast('Marked as Lost', 'success');
        closeLostModal();
        loadLeads();
    } else {
        showToast(res.error || 'Error', 'error');
    }
}

// ─── UTILS ────────────────────────────────────────────────────────────────────

// Feature 6: jump from intake to job in All Jobs tab
function jumpToJob(jobId) {
    switchTab('jobs');
    // Highlight the row after the table loads
    setTimeout(() => {
        const rows = document.querySelectorAll('#jobs-tbody tr');
        rows.forEach(row => {
            row.classList.remove('row-highlight');
            // Match by checking any onclick attribute containing this job id
            if (row.innerHTML.includes(`editJob(${jobId})`)) {
                row.classList.add('row-highlight');
                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }, 500);
}

// Feature 5: print intake sheet
function printLeadSheet() {
    const fields = {
        'Caller': document.getElementById('lead-client-name')?.value,
        'Property Owner': document.getElementById('lead-property-owner')?.value,
        'Phone': document.getElementById('lead-client-phone')?.value,
        'Email': document.getElementById('lead-client-email')?.value,
        'Property Address': document.getElementById('lead-address')?.value,
        'County': document.getElementById('lead-county')?.value,
        'Size': document.getElementById('lead-approx-size')?.value,
        'Property Type': _getRadio('prop-type'),
        'Purpose': _getCheckboxes('survey-purpose') + (document.getElementById('lead-survey-purpose-other')?.value ? ', ' + document.getElementById('lead-survey-purpose-other').value : ''),
        'Condition': _getRadio('prop-condition'),
        'Improvements': _getCheckboxes('improvements') + (document.getElementById('lead-improvements-other')?.value ? ', ' + document.getElementById('lead-improvements-other').value : ''),
        'Terrain': _getCheckboxes('terrain') + (document.getElementById('lead-terrain-details')?.value ? ' — ' + document.getElementById('lead-terrain-details').value : ''),
        'Site Risks': _getCheckboxes('site-risks') + (document.getElementById('lead-risks-other')?.value ? ', ' + document.getElementById('lead-risks-other').value : ''),
        'Access': _getRadio('access'),
        'Existing Docs': _getCheckboxes('exist-docs'),
        'Existing Markers': _getCheckboxes('exist-markers'),
        'Survey Type(s)': _getCheckboxes('survey-types'),
        'Staking': _getRadio('staking'),
        'Disputes': _getRadio('disputes') + (document.getElementById('lead-disputes-details')?.value ? ' — ' + document.getElementById('lead-disputes-details').value : ''),
        'Needed By': document.getElementById('lead-needed-by')?.value,
        'Timeline': _getRadio('timeline-type') + (document.getElementById('lead-timeline-other')?.value ? ', ' + document.getElementById('lead-timeline-other').value : ''),
        'Deliverables': _getCheckboxes('deliverables') + (document.getElementById('lead-deliverables-other')?.value ? ', ' + document.getElementById('lead-deliverables-other').value : ''),
        'Coordination': _getCheckboxes('coordination') + (document.getElementById('lead-coordination-details')?.value ? ' — ' + document.getElementById('lead-coordination-details').value : ''),
        'Referral': _getRadio('referral') + (document.getElementById('lead-referral-other')?.value ? ', ' + document.getElementById('lead-referral-other').value : ''),
        'Notes': document.getElementById('lead-description')?.value,
        'Summary': document.getElementById('lead-key-notes')?.value,
        'Deadline': document.getElementById('lead-deadline')?.value
    };

    const rows = Object.entries(fields)
        .filter(([, v]) => v)
        .map(([k, v]) => `<tr><td style="font-weight:600;padding:5px 12px 5px 0;vertical-align:top;white-space:nowrap;color:#1B3A5C">${k}</td><td style="padding:5px 0">${v}</td></tr>`)
        .join('');

    const name = document.getElementById('lead-client-name')?.value || 'Intake';
    const html = `<!DOCTYPE html><html><head><title>Survey Request — ${name}</title>
    <style>
        body { font-family: Arial, sans-serif; font-size: 13px; margin: 24px; color: #1F2937; }
        h1 { font-size: 18px; color: #1B3A5C; margin-bottom: 4px; }
        .subtitle { color: #6B7280; font-size: 12px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        td { border-bottom: 1px solid #E5E7EB; }
        @media print { body { margin: 12px; } }
    </style></head><body>
    <h1>White Stone Geomatics — Survey Request</h1>
    <div class="subtitle">Printed ${new Date().toLocaleDateString('en-US', {weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
    <table>${rows}</table>
    </body></html>`;

    const win = window.open('', '_blank');
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 400);
}

function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function formatTime(t) {
    if (!t) return '';
    const [h, m] = t.split(':').map(Number);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hr = h % 12 || 12;
    return `${hr}:${String(m).padStart(2, '0')} ${ampm}`;
}
