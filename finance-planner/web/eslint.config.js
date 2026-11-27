import stylistic from "@stylistic/eslint-plugin";
import { defineConfigWithVueTs, vueTsConfigs } from "@vue/eslint-config-typescript";
import { globalIgnores } from "eslint/config";
import pluginVue from "eslint-plugin-vue";

const MAX_LINE_LENGTH = 150;
const INDENT_SIZE = 4;

export default defineConfigWithVueTs(
    {
        name: "planner/files",
        files: ["**/*.{js,ts,vue}"],
    },
    globalIgnores(["dist/**", "node_modules/**"]),
    pluginVue.configs["flat/recommended"],
    vueTsConfigs.recommended,
    {
        name: "planner/style",
        plugins: {
            "@stylistic": stylistic,
        },
        rules: {
            "curly": ["error", "all"],
            "eqeqeq": ["error", "always"],
            "no-var": "error",
            "prefer-const": "error",
            "@stylistic/brace-style": ["error", "1tbs"],
            "@stylistic/comma-dangle": ["error", "always-multiline"],
            "@stylistic/eol-last": ["error", "always"],
            "@stylistic/indent": ["error", INDENT_SIZE, { SwitchCase: 1 }],
            "@stylistic/max-len": ["error", { code: MAX_LINE_LENGTH, ignoreUrls: true }],
            "@stylistic/no-multiple-empty-lines": ["error", { max: 1, maxBOF: 0, maxEOF: 0 }],
            "@stylistic/no-trailing-spaces": "error",
            "@stylistic/quotes": ["error", "double"],
            "@stylistic/semi": ["error", "always"],
            "vue/html-indent": ["error", INDENT_SIZE],
            // Элемент, который помещается в строку, пишется в одну строку, длинный разбивается по атрибуту на строку
            "vue/max-attributes-per-line": ["error", { singleline: { max: 20 }, multiline: { max: 1 } }],
            "vue/singleline-html-element-content-newline": "off",
            "vue/multi-word-component-names": "off",
        },
    },
);
