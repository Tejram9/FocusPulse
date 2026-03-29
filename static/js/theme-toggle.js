document.addEventListener('DOMContentLoaded', () => {
    const toggleBtns = document.querySelectorAll('#themeToggleBtn, #themeToggleBtnOut');

    // Check local storage
    const currentTheme = localStorage.getItem('theme') || 'light';

    if (currentTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        toggleBtns.forEach(btn => btn.textContent = '☀️');
    }

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            let theme = document.documentElement.getAttribute('data-theme');
            if (theme === 'dark') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                toggleBtns.forEach(b => b.textContent = '🌙');
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                toggleBtns.forEach(b => b.textContent = '☀️');
            }
        });
    });
});
