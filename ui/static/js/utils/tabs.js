export const switchToTab = (btnId) => {
    // ✅ Switch to "Oversight" or  tab automatically
    const btn = document.getElementById(btnId);
    if (btn && window.bootstrap?.Tab) {
        bootstrap.Tab.getOrCreateInstance(btn).show();
    } else if (btn) {
        // fallback: trigger click if bootstrap isn't on window for some reason
        btn.click();
    }
}
