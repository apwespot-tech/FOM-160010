// Ключи запросов TanStack Query собраны в одном месте: по ним же после изменений помечаются устаревшими зависящие данные
export const queryKeys = {
    accounts: ["accounts"] as const,
    categories: ["categories"] as const,
    operations: ["operations"] as const,
};
