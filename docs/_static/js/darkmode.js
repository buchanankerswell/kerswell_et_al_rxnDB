document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.createElement("button");
    toggle.innerText = "🌙 Dark Mode";
    toggle.style.position = "fixed";
    toggle.style.bottom = "10px";
    toggle.style.right = "10px";
    toggle.style.padding = "5px 10px";
    toggle.style.border = "none";
    toggle.style.cursor = "pointer";
    toggle.style.zIndex = "1000";
//    toggle.style.transition = "background 0.2s, color 0.2s";

    function updateToggleStyle() {
        if (document.documentElement.classList.contains("dark-mode")) {
            toggle.innerText = "☀️ Light Mode";
            toggle.style.background = getComputedStyle(document.documentElement).getPropertyValue("--bg");
            toggle.style.color = getComputedStyle(document.documentElement).getPropertyValue("--text");
        } else {
            toggle.innerText = "🌙 Dark Mode";
            toggle.style.background = getComputedStyle(document.documentElement).getPropertyValue("--bg");
            toggle.style.color = getComputedStyle(document.documentElement).getPropertyValue("--text");
        }
    }

    toggle.addEventListener("click", function () {
        if (document.documentElement.classList.contains("dark-mode")) {
            document.documentElement.classList.remove("dark-mode");
            localStorage.setItem("theme", "light");
        } else {
            document.documentElement.classList.add("dark-mode");
            localStorage.setItem("theme", "dark");
        }
        updateToggleStyle();
    });

    document.body.appendChild(toggle);

    // Check user preference and apply correct styles
    if (localStorage.getItem("theme") === "dark") {
        document.documentElement.classList.add("dark-mode");
    }
    updateToggleStyle();
});
