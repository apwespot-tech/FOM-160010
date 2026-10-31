import 'primeicons/primeicons.css'
import './styles.css'

import { createPinia } from 'pinia'
import ru from 'primelocale/ru.json'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { createApp } from 'vue'

import App from './App.vue'
import { createAppRouter } from './router'
import { themeOptions } from './theme'

const app = createApp(App)

app.use(createPinia())
app.use(createAppRouter())
app.use(PrimeVue, { theme: themeOptions, locale: ru.ru })
app.use(ToastService)

app.mount('#app')
