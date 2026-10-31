import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach } from 'vitest'

import { installMatchMedia, setViewportWidth } from './helpers/media'

enableAutoUnmount(afterEach)

beforeEach(() => {
  installMatchMedia()
  setViewportWidth(1280)
  localStorage.clear()
})
