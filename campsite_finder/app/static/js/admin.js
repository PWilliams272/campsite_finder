function toggleActive(checkboxEl, uuid, token, checked) {
    fetch(`/toggle_active/${uuid}?token=${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: checked })
    }).then(r => {
        if (!r.ok) {
            alert('Failed to update status!');
            checkboxEl.checked = !checked;
            return;
        }
        const badge = checkboxEl.closest('.config-card-head').querySelector('.badge');
        badge.textContent = checked ? 'Active' : 'Inactive';
        badge.classList.toggle('badge-active', checked);
        badge.classList.toggle('badge-inactive', !checked);
    });
}

function deleteConfig(uuid, token) {
    if (!confirm('Are you sure you want to delete this configuration? This action cannot be undone.')) return;
    fetch(`/delete_config/${uuid}?token=${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    }).then(r => {
        if (r.ok) {
            location.reload();
        } else {
            alert('Failed to delete configuration!');
        }
    });
}
