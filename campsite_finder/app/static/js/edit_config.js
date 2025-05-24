// edit_config.js: Prepopulate and handle update/delete for edit config page

document.addEventListener('DOMContentLoaded', function() {
    // Prepopulate name
    document.getElementById('user-name').value = PREPOP_CONFIG.name || '';

    // Prepopulate emails
    window.emailList = Array.isArray(PREPOP_CONFIG.email_to) ? PREPOP_CONFIG.email_to.slice() : [];
    if (window.renderEmailList) renderEmailList();
    else {
        // fallback: render badges manually
        const emailListDiv = document.getElementById('email-list');
        emailListDiv.innerHTML = '';
        window.emailList.forEach(email => {
            const badge = document.createElement('span');
            badge.className = 'badge rounded-pill bg-info me-2 mb-1 d-inline-flex align-items-center';
            badge.innerHTML = `<span>${email}</span>`;
            emailListDiv.appendChild(badge);
        });
    }

    // Prepopulate checkboxes
    document.getElementById('allow-partial').checked = !!PREPOP_CONFIG.Partial;
    document.getElementById('tents-permitted').checked = !!PREPOP_CONFIG.TentsPermitted;

    // Prepopulate date range using Litepicker if available
    if (window.picker && PREPOP_CONFIG.start_date && PREPOP_CONFIG.end_date) {
        window.picker.setDateRange(PREPOP_CONFIG.start_date, PREPOP_CONFIG.end_date);
    } else if (PREPOP_CONFIG.start_date && PREPOP_CONFIG.end_date) {
        // fallback: set input value
        document.getElementById('date-range').value = PREPOP_CONFIG.start_date + ' to ' + PREPOP_CONFIG.end_date;
    }

    // Prepopulate campgrounds and parks
    if (PREPOP_CONFIG.campgrounds) {
        // Try to infer selected parks from campgrounds if possible
        // This assumes you have a mapping of campgrounds to parks in your JS (or fetch it)
        // For now, just select the campgrounds by name/id
        window.selectedCampgrounds = {};
        Object.entries(PREPOP_CONFIG.campgrounds).forEach(([cgName, cgId]) => {
            window.selectedCampgrounds[cgId] = cgName;
        });
        if (window.renderSelectedCampgrounds) renderSelectedCampgrounds();
        // Optionally, trigger UI to show campgrounds section
        document.getElementById('campgrounds-section').style.display = '';
    }

    // Update button handler (already handled by form submit in template)
    // Delete button handler
    document.getElementById('deleteBtn').onclick = function() {
        if (confirm('Are you sure you want to delete this configuration?')) {
            fetch(API_ENDPOINTS.deleteConfig, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            }).then(r => {
                if (r.ok) window.location.href = "{{ url_for('campsite_finder.admin') }}";
                else alert('Failed to delete configuration!');
            });
        }
    };
});
