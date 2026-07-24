function showSearch(type) {
    document.getElementById('team-search').style.display = type === 'team' ? 'block' : 'none';
    document.getElementById('player-search').style.display = type === 'player' ? 'block' : 'none';

    document.querySelectorAll('.search-tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
}

function toggleTheme() {
    const html = document.documentElement;
    const isLight = html.getAttribute('data-theme') === 'light';

    if (isLight) {
        html.removeAttribute('data-theme');
        localStorage.setItem('scoutview-theme', 'dark');
    } else {
        html.setAttribute('data-theme', 'light');
        localStorage.setItem('scoutview-theme', 'light');
    }

    updateThemeToggleIcon();
}

function updateThemeToggleIcon() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    btn.textContent = isLight ? '☀️' : '🌙';
    btn.setAttribute('aria-label', isLight ? 'Switch to dark mode' : 'Switch to light mode');
}

document.addEventListener('DOMContentLoaded', updateThemeToggleIcon);