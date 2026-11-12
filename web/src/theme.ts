import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

// Фиолетовая шкала — основной цвет (кнопки, ссылки, фокус)
const violet = {
  50: '#f5f3ff',
  100: '#ede9fe',
  200: '#ddd6fe',
  300: '#c4b5fd',
  400: '#a78bfa',
  500: '#8b5cf6',
  600: '#7c3aed',
  700: '#6d28d9',
  800: '#5b21b6',
  900: '#4c1d95',
  950: '#2e1065',
}

// Нейтральные поверхности с лёгким фиолетовым оттенком
const surface = {
  0: '#ffffff',
  50: '#f8f7fc',
  100: '#f1eff8',
  200: '#e7e5ef',
  300: '#d4d1e0',
  400: '#a9a5bb',
  500: '#6b6780',
  600: '#4f4b63',
  700: '#3a364d',
  800: '#2a2639',
  900: '#1f1b2e',
  950: '#14111f',
}

export const AppPreset = definePreset(Aura, {
  semantic: {
    primary: violet,
    formField: {
      // Высота полей ровно 44 px при шрифте 16 px: 9 + 24 (строка) + 9 + 2 (рамка)
      paddingY: '0.5625rem',
    },
    colorScheme: {
      light: {
        surface,
        primary: {
          color: '{primary.700}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.800}',
          activeColor: '{primary.900}',
        },
        text: {
          color: '{surface.900}',
          hoverColor: '{surface.950}',
          mutedColor: '{surface.500}',
          hoverMutedColor: '{surface.600}',
        },
        formField: {
          color: '{surface.900}',
        },
      },
      // Тёмная тема добавится здесь (colorScheme.dark) и включится классом .app-dark
    },
  },
})

export const themeOptions = {
  preset: AppPreset,
  options: {
    darkModeSelector: '.app-dark',
  },
}
