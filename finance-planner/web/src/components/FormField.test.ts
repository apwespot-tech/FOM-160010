import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { h } from "vue";

import FormField from "./FormField.vue";

afterEach(() => {
    document.body.innerHTML = "";
});

describe("FormField", () => {
    it("builds the label and hint ids from the field id", () => {
        const wrapper = mount(FormField, { props: { label: "Сумма", inputId: "amount", hint: "Например 1250.50" } });
        const label = wrapper.get("label");

        expect(label.attributes("id")).toBe("amount-label");
        expect(label.attributes("for")).toBe("amount");
        expect(wrapper.get("#amount-hint").text()).toBe("Например 1250.50");
    });

    it("shows the error instead of the hint", () => {
        const props = { label: "Сумма", inputId: "amount", hint: "Например 1250.50", error: "Введите сумму" };
        const wrapper = mount(FormField, { props });
        const error = wrapper.get("#amount-error");

        expect(wrapper.find("#amount-hint").exists()).toBe(false);
        expect(error.attributes("role")).toBe("alert");
        expect(error.text()).toBe("Введите сумму");
    });

    it("hides the required mark from screen readers", () => {
        const wrapper = mount(FormField, { props: { label: "Счёт", inputId: "account", isRequired: true } });

        expect(wrapper.get(".form-field__required").attributes("aria-hidden")).toBe("true");
    });

    it("focuses a selection field that the label cannot focus by itself", async () => {
        const selectionField = () => h("span", { id: "account", tabindex: 0, role: "combobox" }, "Карта");

        const wrapper = mount(FormField, {
            props: { label: "Счёт", inputId: "account" },
            slots: { default: selectionField },
            attachTo: document.body,
        });

        await wrapper.get("label").trigger("click");

        expect(document.activeElement?.id).toBe("account");
        wrapper.unmount();
    });
});
