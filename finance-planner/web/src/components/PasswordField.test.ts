import { mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import { describe, expect, it } from "vitest";

import PasswordField from "./PasswordField.vue";

function mountPasswordField() {
    return mount(PasswordField, {
        props: {
            modelValue: "quiet-river-2026",
            inputId: "login-password",
            autocomplete: "current-password",
            description: { "aria-describedby": "login-password-error", "aria-invalid": "true" },
            isInvalid: true,
        },
        global: { plugins: [PrimeVue] },
    });
}

describe("PasswordField", () => {
    it("passes the field id and its description to the input", () => {
        const input = mountPasswordField().get("input");

        expect(input.attributes("id")).toBe("login-password");
        expect(input.attributes("aria-describedby")).toBe("login-password-error");
        expect(input.attributes("autocomplete")).toBe("current-password");
    });

    it("shows and hides the password with a button that keyboard users can reach", async () => {
        const wrapper = mountPasswordField();
        const toggle = wrapper.get("button");

        expect(wrapper.get("input").attributes("type")).toBe("password");
        expect(toggle.attributes("type")).toBe("button");
        expect(toggle.attributes("aria-label")).toBe("Показать пароль");

        await toggle.trigger("click");

        expect(wrapper.get("input").attributes("type")).toBe("text");
        expect(toggle.attributes("aria-label")).toBe("Скрыть пароль");
    });
});
