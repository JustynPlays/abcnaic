// Admin Users JavaScript


document.addEventListener('DOMContentLoaded', function() {
    // Reset button functionality
    const resetBtn = document.getElementById('resetSearchBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            const resetUrl = this.getAttribute('data-reset-url');
            if (resetUrl) {
                window.location.href = resetUrl;
            }
        });
    }

    // 'Select all' checkbox functionality
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.user-checkbox');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');

    if(selectAll) {
        selectAll.addEventListener('change', function() {
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAll.checked;
            });
            toggleBulkDeleteButton();
        });
    }

    // Individual checkbox functionality
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            toggleBulkDeleteButton();
            // Update select all checkbox state
            const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
            if (selectAll) {
                selectAll.checked = checkedBoxes.length === checkboxes.length;
                selectAll.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < checkboxes.length;
            }
        });
    });

    // Bulk delete button functionality
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', function() {
            const selectedUsers = document.querySelectorAll('.user-checkbox:checked');
            if (selectedUsers.length === 0) {
                alert('Please select users to delete.');
                return;
            }

            const userIds = Array.from(selectedUsers).map(cb => cb.value);
            const userNames = Array.from(selectedUsers).map(cb => {
                const row = cb.closest('tr');
                return row.querySelector('td:nth-child(2)').textContent.trim();
            });

            if (confirm(`Are you sure you want to delete ${selectedUsers.length} user(s)?\n\nUsers: ${userNames.join(', ')}`)) {
                document.getElementById('bulkDeleteUserIds').value = userIds.join(',');
                document.getElementById('bulkDeleteForm').submit();
            }
        });
    }

    function toggleBulkDeleteButton() {
        const selectedUsers = document.querySelectorAll('.user-checkbox:checked');
        if (bulkDeleteBtn) {
            bulkDeleteBtn.style.display = selectedUsers.length > 0 ? 'inline-block' : 'none';
        }
    }
});
