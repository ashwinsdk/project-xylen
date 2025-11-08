/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'xylen-red': {
                    900: '#5C0000',
                    800: '#8B0000',
                    700: '#A50000',
                    600: '#C00000',
                },
                'xylen-dark': {
                    950: '#000000',
                    900: '#0A0A0A',
                    800: '#1A1A1A',
                    700: '#2A2A2A',
                }
            },
            backgroundImage: {
                'xylen-gradient': 'linear-gradient(180deg, #5C0000, #8B0000)',
                'xylen-gradient-hover': 'linear-gradient(180deg, #6C0000, #9B0000)',
            },
            fontFamily: {
                'sans': ['Inter', 'system-ui', 'sans-serif'],
                'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
            },
        },
    },
    plugins: [],
}
