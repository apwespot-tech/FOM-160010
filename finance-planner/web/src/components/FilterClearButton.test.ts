import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FilterClearButton from "./FilterClearButton.vue";

describe("FilterClearButton", () => {
    it("is a named button that the Select treats as its clear icon", async () => {
        const wrapper = mount(FilterClearButton, { props: { label: "Снять фильтр по счёту" } });
        const button = wrapper.get("button");

        await button.trigger("click");

        expect(button.attributes("type")).toBe("button");
        expect(button.attributes("aria-label")).toBe("Снять фильтр по счёту");
        expect(button.attributes("data-pc-section")).toBe("clearicon");
        expect(wrapper.emitted("clear")).toHaveLength(1);
    });
});
