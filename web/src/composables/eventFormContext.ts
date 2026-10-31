import { inject, provide, type InjectionKey } from 'vue'

import type { useEventForm } from './useEventForm'

export type EventFormController = ReturnType<typeof useEventForm>

const KEY: InjectionKey<EventFormController> = Symbol('event-form')

/** Делит одну форму между окном создания или страницей мероприятия и полями ввода. */
export function provideEventForm(controller: EventFormController): void {
  provide(KEY, controller)
}

export function injectEventForm(): EventFormController {
  const controller = inject(KEY)
  if (!controller) throw new Error('EventFieldInput используется вне формы мероприятия')
  return controller
}
