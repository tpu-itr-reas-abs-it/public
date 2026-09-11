import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

export const preset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#fdf3f3',
      100: '#fbe5e5',
      200: '#f7cccc',
      300: '#f0a5a5',
      400: '#e37474',
      500: '#c64747',
      600: '#b03a3a',
      700: '#922e2e',
      800: '#7a2929',
      900: '#680202',
      950: '#3f0101',
    },
    colorScheme: {
      light: {
        primary: {
          color: '{primary.500}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.900}',
          activeColor: '{primary.800}',
        },
        highlight: {
          background: '{primary.50}',
          focusBackground: '{primary.100}',
          color: '{primary.700}',
          focusColor: '{primary.800}',
        },
      },
    },
  },
})
