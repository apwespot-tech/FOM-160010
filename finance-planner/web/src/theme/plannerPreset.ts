import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura";

// Тёмная схема Aura берёт цвета из переменных палитры main.css: компоненты PrimeVue совпадают с остальными страницами,
// а текст не становится чисто белым, как в Aura по умолчанию
export const plannerPreset = definePreset(Aura, {
    semantic: {
        primary: {
            50: "#eef3fd",
            100: "#dce7fb",
            200: "#c2d4f8",
            300: "var(--color-accent-hover)",
            400: "var(--color-accent)",
            500: "#668fe0",
            600: "#5478c4",
            700: "#4461a0",
            800: "#374f80",
            900: "#2d4066",
            950: "#1d2a44",
        },
        colorScheme: {
            dark: {
                surface: {
                    0: "#ffffff",
                    50: "#f4f6f9",
                    100: "#e8ecf1",
                    200: "var(--color-text)",
                    300: "var(--color-text-secondary)",
                    400: "var(--color-text-tertiary)",
                    500: "#7b8695",
                    600: "var(--color-border-strong)",
                    700: "var(--color-border)",
                    800: "var(--color-surface-raised)",
                    900: "var(--color-surface)",
                    950: "var(--color-canvas)",
                },
                primary: {
                    color: "var(--color-accent)",
                    contrastColor: "var(--color-on-accent)",
                    hoverColor: "var(--color-accent-hover)",
                    activeColor: "var(--color-accent-hover)",
                },
                highlight: {
                    color: "var(--color-text)",
                    focusColor: "var(--color-text)",
                },
                text: {
                    color: "var(--color-text)",
                    hoverColor: "var(--color-text)",
                    mutedColor: "var(--color-text-secondary)",
                    hoverMutedColor: "var(--color-text)",
                },
                formField: {
                    color: "var(--color-text)",
                    placeholderColor: "var(--color-text-tertiary)",
                    invalidBorderColor: "var(--color-danger)",
                    invalidPlaceholderColor: "var(--color-danger)",
                },
            },
        },
    },
});
