// Global theme configuration
export const theme = {
    colors: {
        primary: '#00ff00',
        background: 'rgba(26, 26, 26, 0.95)',
        text: '#ffffff',
        border: '#333',
        error: '#ff5555',
        warning: '#ffaa00'
    },
    sizes: {
        borderRadius: '8px',
        padding: '15px'
    },
    effects: {
        glow: '0 4px 16px rgba(0, 255, 0, 0.3)',
        blur: 'blur(10px)'
    }
};

export const animations = {
    buttonHover: `
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0, 255, 0, 0.4);
    `,
    fadeIn: `
        opacity: 1;
        transition: opacity 0.3s ease-in-out;
    `
};
