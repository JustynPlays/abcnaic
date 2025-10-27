// Simple Body Diagram Interaction Script
document.addEventListener('DOMContentLoaded', function() {
    const bodyParts = document.querySelectorAll('.body-part');
    const selectedPartsContainer = document.getElementById('selected-body-parts');
    const biteLocationInput = document.getElementById('bite_location');
    let selectedParts = [];

    // Initialize selected parts from hidden input if exists
    if (biteLocationInput && biteLocationInput.value) {
        selectedParts = biteLocationInput.value.split(',').filter(part => part.trim());
        updateSelectedParts();
    }

    bodyParts.forEach(part => {
        part.addEventListener('click', function() {
            const partName = this.getAttribute('data-part');

            if (selectedParts.includes(partName)) {
                // Deselect the part
                selectedParts = selectedParts.filter(p => p !== partName);
                this.classList.remove('selected');
            } else {
                // Select the part
                selectedParts.push(partName);
                this.classList.add('selected');
            }

            // Update the hidden input
            if (biteLocationInput) {
                biteLocationInput.value = selectedParts.join(',');
            }

            // Update the display
            updateSelectedParts();
        });
    });

    function updateSelectedParts() {
        if (selectedPartsContainer) {
            selectedPartsContainer.innerHTML = '';

            if (selectedParts.length === 0) {
                selectedPartsContainer.innerHTML = `
                    <div class="text-center py-4">
                        <p class="text-muted mb-2">No body parts selected</p>
                        <small class="text-gray-500">Click on the body diagram to select where you were bitten or scratched</small>
                    </div>
                `;
                return;
            }

            // Summary header
            const title = document.createElement('div');
            title.className = 'mb-3';
            title.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-0" style="color: #b20000;">Selected Areas (${selectedParts.length})</h5>
                </div>
            `;
            selectedPartsContainer.appendChild(title);

            // Selected parts list
            selectedParts.forEach(part => {
                const badgeContainer = document.createElement('div');
                badgeContainer.className = 'd-flex justify-content-between align-items-center mb-2 p-2 bg-light rounded';

                const badge = document.createElement('span');
                badge.className = 'badge bg-danger';
                badge.innerHTML = formatBodyPartName(part);

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'btn btn-sm btn-outline-danger';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = () => removeBodyPart(part);

                badgeContainer.appendChild(badge);
                badgeContainer.appendChild(removeBtn);
                selectedPartsContainer.appendChild(badgeContainer);
            });
        }
    }

    function formatBodyPartName(partName) {
        return partName.split('-').map(word =>
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    // Clear all selections
    const clearButton = document.getElementById('clear-body-parts');
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            selectedParts = [];
            bodyParts.forEach(part => part.classList.remove('selected'));
            if (biteLocationInput) {
                biteLocationInput.value = '';
            }
            updateSelectedParts();
        });
    }

    // Initialize
    setTimeout(updateSelectedParts, 100);
});

// Function to remove individual body part (called from onclick)
function removeBodyPart(partName) {
    const bodyParts = document.querySelectorAll('.body-part');
    const biteLocationInput = document.getElementById('bite_location');
    const selectedPartsContainer = document.getElementById('selected-body-parts');
    let selectedParts = [];

    // Get current selections
    if (biteLocationInput && biteLocationInput.value) {
        selectedParts = biteLocationInput.value.split(',').filter(part => part.trim());
    }

    // Remove the specific part
    selectedParts = selectedParts.filter(p => p !== partName);

    // Update the input
    if (biteLocationInput) {
        biteLocationInput.value = selectedParts.join(',');
    }

    // Remove visual selection
    bodyParts.forEach(part => {
        if (part.getAttribute('data-part') === partName) {
            part.classList.remove('selected');
        }
    });

    // Update display
    const event = new CustomEvent('updateSelectedParts');
    document.dispatchEvent(event);
}
