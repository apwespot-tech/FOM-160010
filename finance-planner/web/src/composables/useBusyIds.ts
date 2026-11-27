import { ref } from "vue";

// Записи, по которым ещё идёт запрос. Их кнопки недоступны, чтобы повторное нажатие не отправило второй DELETE
export function useBusyIds() {
    const busyIds = ref<ReadonlySet<number>>(new Set());

    function markBusy(id: number): void {
        busyIds.value = new Set([...busyIds.value, id]);
    }

    function releaseBusy(id: number): void {
        const nextIds = new Set(busyIds.value);

        nextIds.delete(id);
        busyIds.value = nextIds;
    }

    return {
        busyIds,
        markBusy,
        releaseBusy,
    };
}
