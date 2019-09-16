// https://eslint.org/docs/user-guide/configuring

module.exports = {
  root: true,
  parserOptions: {
    parser: 'babel-eslint'
  },
  env: {
    browser: true,
  },
  extends: [
    // https://github.com/vuejs/eslint-plugin-vue#priority-a-essential-error-prevention
    // consider switching to `plugin:vue/strongly-recommended` or `plugin:vue/recommended` for stricter rules.
    'plugin:vue/essential', 
    // https://github.com/standard/standard/blob/master/docs/RULES-en.md
    'standard'
  ],
  // required to lint *.vue files
  plugins: [
    'vue'
  ],
  // add your custom rules here
  rules: {
    // Allow async-await.
    'generator-star-spacing': 'off',
    // Allow debugger during development.
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    // Trailing commas are just fine,
    'comma-dangle': 'off',
    // Blank lines at end are nice.
    'no-multiple-empty-lines': ['error', {'max': 2}],
    // No one cares about end of line whitespace.
    'no-trailing-spaces': 'off',
    'no-multi-spaces': 'off',

    'space-before-function-paren': ["error", {"anonymous": "always", "named": "never", "asyncArrow": "always"}],
    'vue/require-v-for-key': 'off',
    'curly': ['error', 'multi'],
    'camelcase': 'off',
    'indent': 'off',
    'operator-linebreak': 'off',
    'space-in-parens': 'off',
    'key-spacing': 'off',
    'brace-style': 'off',
    'yield-star-spacing': 'off',
  }
}
