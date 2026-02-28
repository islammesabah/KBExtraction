/**
 * Tiny Emoji Confetti 🎊
 * ----------------------
 * No libraries. Just a few emoji particles that fly/fall and get removed.
 */

const EMOJIS = ["🎉", "✨", "🎊", "✅"];

export function fireConfetti() {
    // Create a temporary container
    const box = document.createElement("div");
    box.className = "confetti-box";
    document.body.appendChild(box);

    const n = 18; // number of particles
    for (let i = 0; i < n; i++) {
        const el = document.createElement("div");
        el.className = "confetti-particle";
        el.textContent = EMOJIS[i % EMOJIS.length];

        // Start near top-right (where toast is)
        const x = window.innerWidth - 80 + rand(-40, 20);
        const y = 40 + rand(-10, 10);

        el.style.left = `${x}px`;
        el.style.top = `${y}px`;

        // Random motion
        el.style.setProperty("--dx", `${rand(-120, 40)}px`);
        el.style.setProperty("--dy", `${rand(140, 260)}px`);
        el.style.setProperty("--rot", `${rand(-220, 220)}deg`);
        el.style.animationDuration = `${rand(700, 1100)}ms`;

        box.appendChild(el);
    }

    // Cleanup
    setTimeout(() => box.remove(), 1400);
}

function rand(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
