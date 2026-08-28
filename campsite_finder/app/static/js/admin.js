function toggleActive(uuid, checked) {
    fetch(`/toggle_active/${uuid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: checked })
    }).then(r => {
        if (!r.ok) alert('Failed to update status!');
    });
}

function deleteConfig(uuid) {
    if (!confirm('Are you sure you want to delete this configuration? This action cannot be undone.')) return;
    fetch(`/delete_config/${uuid}`, {
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
