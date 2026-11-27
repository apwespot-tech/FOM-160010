import type { Category, CategoryBody } from "../types/ledger";
import { requestJson } from "./apiClient";

interface CategoryListBody {
    items: CategoryBody[];
}

function toCategory(body: CategoryBody): Category {
    return {
        id: body.id,
        name: body.name,
        kind: body.kind,
        isCommon: body.is_common,
    };
}

export async function fetchCategories(): Promise<Category[]> {
    const body = await requestJson<CategoryListBody>("/api/categories");

    return body.items.map(toCategory);
}
