/**
 * Frontend Unit Test Suite for FormManager & NavigationGuard
 * Verifies that typing/editing does NOT fire network requests and that DB updates occur ONLY on Save.
 */

// Mock DOM structure
function createMockForm() {
    const container = document.createElement('div');
    container.id = 'testForm';
    container.innerHTML = `
        <input type="text" id="company_name" name="company_name" value="ABC Pvt Ltd" />
        <input type="checkbox" id="notifications" name="notifications" checked />
        <select id="industry" name="industry">
            <option value="Manufacturing" selected>Manufacturing</option>
            <option value="Automotive">Automotive</option>
        </select>
        <button id="saveBtn" disabled>Save Changes</button>
        <button id="cancelBtn" disabled>Cancel</button>
        <span id="unsavedBadge" class="d-none">Unsaved Changes</span>
    `;
    document.body.appendChild(container);
    return container;
}

function testFormManagerWorkflow() {
    console.log("--- Starting FormManager Workflow Verification ---");
    const formEl = createMockForm();
    let saveCallCount = 0;
    let savedPayload = null;

    const fm = new window.FormManager({
        container: '#testForm',
        saveBtn: '#saveBtn',
        cancelBtn: '#cancelBtn',
        badge: '#unsavedBadge',
        onSave: async (payload) => {
            saveCallCount++;
            savedPayload = payload;
            return true;
        }
    });

    fm.initData();

    // 1. Initial State Check
    console.assert(fm.isDirty === false, "Initial isDirty state must be false");
    console.assert(saveCallCount === 0, "Zero save requests should exist initially");

    // 2. Typing Simulation ("ABC Private Ltd")
    const input = document.getElementById('company_name');
    input.value = "A";
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.value = "AB";
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.value = "ABC Private Ltd";
    input.dispatchEvent(new Event('input', { bubbles: true }));

    // Verify typing changed ONLY local state
    console.assert(fm.isDirty === true, "isDirty must be true after typing");
    console.assert(saveCallCount === 0, "NO network API call should occur while typing!");
    console.assert(document.getElementById('saveBtn').disabled === false, "Save button must be enabled");

    // 3. Cancel Action Verification
    fm.cancel();
    console.assert(input.value === "ABC Pvt Ltd", "Cancel must restore original value");
    console.assert(fm.isDirty === false, "isDirty must reset to false after Cancel");
    console.assert(saveCallCount === 0, "Cancel must make ZERO API calls");

    // 4. Explicit Save Action Verification
    input.value = "ABC Private Ltd";
    input.dispatchEvent(new Event('input', { bubbles: true }));
    
    fm.save().then(() => {
        console.assert(saveCallCount === 1, "Save button must trigger exactly ONE API call");
        console.assert(savedPayload.company_name === "ABC Private Ltd", "Payload must contain changed field");
        console.assert(fm.isDirty === false, "isDirty must reset to false after successful Save");
        console.log("PASSED: FormManager transactional workflow verified successfully!");
        formEl.remove();
    });
}

if (typeof window !== 'undefined') {
    window.testFormManagerWorkflow = testFormManagerWorkflow;
}
