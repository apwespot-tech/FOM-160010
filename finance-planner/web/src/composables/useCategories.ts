import { useQuery } from "@tanstack/vue-query";

import { fetchCategories } from "../services/categoriesApi";
import { queryKeys } from "../services/queryKeys";

export function useCategoriesQuery() {
    return useQuery({
        queryKey: queryKeys.categories,
        queryFn: fetchCategories,
    });
}
